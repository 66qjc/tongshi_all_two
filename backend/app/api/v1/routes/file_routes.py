"""统一文件访问路由"""
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.db.session import get_db
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


@router.get("/files/{file_id}")
def get_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """通过 file_id 统一访问文件，自动分发到本地或 S3 存储。"""
    record, stream = resolve_file_stream(db, file_id)

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
