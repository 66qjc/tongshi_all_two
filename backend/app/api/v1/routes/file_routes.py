"""统一文件访问路由"""
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.response import success
from app.core.security import (
    INVALID_FILE_ACCESS_MESSAGE,
    authenticate_bearer_token,
    create_file_access_token,
    decode_file_access_token,
    get_current_user,
    oauth2_scheme,
)
from app.db.session import get_db
from app.models.entities import User
from app.schemas.common import AuthUser
from app.services.file_service import get_authorized_file_record, resolve_file_stream

router = APIRouter()

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


def _close_stream(stream) -> None:
    close = getattr(stream, "close", None)
    if callable(close):
        close()


class _CloseOnceStream:
    """代理文件流，并确保底层资源最多关闭一次。"""

    def __init__(self, stream):
        self._stream = stream
        self._closed = False

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        _close_stream(self._stream)


class _ClosingStreamingResponse(StreamingResponse):
    """无论响应完成、发送失败还是客户端断开，都关闭文件流。"""

    def __init__(self, content, *, stream, **kwargs):
        self._stream = stream
        super().__init__(content, **kwargs)

    async def __call__(self, scope, receive, send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            _close_stream(self._stream)


def _read_stream(stream):
    try:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        _close_stream(stream)


def _read_range(stream, start: int, end: int):
    try:
        stream.seek(start)
    except (AttributeError, OSError):
        # boto3 StreamingBody 不支持 seek，这里顺序丢弃前置字节。
        remaining = start
        while remaining > 0:
            chunk = stream.read(min(64 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)

    remaining = end - start + 1
    try:
        while remaining > 0:
            chunk = stream.read(min(64 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        _close_stream(stream)


def _parse_range_header(range_header: str, size: int) -> tuple[int, int] | None:
    if size <= 0:
        return None
    match = _RANGE_RE.fullmatch(range_header.strip())
    if not match:
        return None

    start_raw, end_raw = match.groups()
    if not start_raw and not end_raw:
        return None

    if start_raw:
        start = int(start_raw)
        end = int(end_raw) if end_raw else size - 1
    else:
        suffix = int(end_raw)
        if suffix <= 0:
            return None
        start = max(size - suffix, 0)
        end = size - 1

    if end < start:
        return None
    if start >= size:
        return None
    return start, min(end, size - 1)


async def _get_optional_file_user(
    file_id: int,
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthUser | None:
    """文件访问可选鉴权，查询参数只接受当前文件的短时凭据。"""
    if "token" in request.query_params:
        raise BusinessException(401, INVALID_FILE_ACCESS_MESSAGE)

    if "access_token" in request.query_params:
        file_token = request.query_params.get("access_token") or ""
        user_id = decode_file_access_token(file_token, file_id)
        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
        ).first()
        if not user:
            raise BusinessException(401, INVALID_FILE_ACCESS_MESSAGE)
        return AuthUser(
            id=user.id,
            name=user.name,
            role=user.role,
            major=user.major,
            needs_password_change=user.needs_password_change,
        )

    if token:
        return authenticate_bearer_token(token, db)
    return None


@router.post("/files/{file_id}/access-url")
def create_file_access_url(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """校验当前权限后签发五分钟有效的单文件访问 URL。"""
    get_authorized_file_record(
        db,
        file_id,
        current_user,
        allow_anonymous=False,
    )
    token = create_file_access_token(current_user.id, file_id)
    return success({
        "url": f"/api/files/{file_id}?access_token={quote(token, safe='')}",
        "expires_in": 300,
    })


@router.get("/files/{file_id}")
def get_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthUser | None = Depends(_get_optional_file_user),
):
    """通过 file_id 统一访问文件，先校验登录态和业务归属。"""
    record, stream = resolve_file_stream(db, file_id, current_user, enforce_auth=True)

    if record is None:
        raise BusinessException(404, "文件不存在")

    if stream is None:
        raise BusinessException(404, "文件内容已丢失")

    stream = _CloseOnceStream(stream)

    content_type = record.content_type or "application/octet-stream"
    filename = record.original_name or record.stored_name or "download"
    encoded = quote(filename, encoding="utf-8")
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f"inline; filename*=UTF-8''{encoded}",
    }

    file_size = record.size_bytes or 0
    if file_size > 0:
        headers["Content-Length"] = str(file_size)

    range_header = request.headers.get("range")
    if range_header and file_size > 0:
        byte_range = _parse_range_header(range_header, file_size)
        if byte_range is not None:
            start, end = byte_range
            headers.update({
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(end - start + 1),
            })
            return _ClosingStreamingResponse(
                _read_range(stream, start, end),
                stream=stream,
                status_code=206,
                media_type=content_type,
                headers=headers,
            )

    return _ClosingStreamingResponse(
        _read_stream(stream),
        stream=stream,
        media_type=content_type,
        headers=headers,
    )
