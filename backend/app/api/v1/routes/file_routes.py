"""统一文件访问路由"""
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.security import oauth2_scheme
from app.db.session import get_db
from app.models.entities import User
from app.schemas.common import AuthUser
from app.services.file_service import resolve_file_stream

router = APIRouter()

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


def _close_stream(stream) -> None:
    close = getattr(stream, "close", None)
    if callable(close):
        close()


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

    if start >= size:
        return None
    return start, min(end, size - 1)


async def _get_optional_file_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthUser | None:
    """文件访问专用可选鉴权；无 token 时交给服务层判断公开白名单。"""
    if not token and settings.allow_query_token_for_files:
        token = request.query_params.get("token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise BusinessException(401, "无效的认证凭据")
    except JWTError:
        raise BusinessException(401, "无效的认证凭据")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(401, "无效的认证凭据")
    return AuthUser(
        id=user.id,
        name=user.name,
        role=user.role,
        major=user.major,
        needs_password_change=user.needs_password_change,
    )


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
            return StreamingResponse(
                _read_range(stream, start, end),
                status_code=206,
                media_type=content_type,
                headers=headers,
            )

    return StreamingResponse(
        stream,
        media_type=content_type,
        headers=headers,
    )
