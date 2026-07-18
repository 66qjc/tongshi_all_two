"""文件上传路由"""
import hashlib
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form

from app.core.config import settings
from app.core.security import get_current_user
from app.core.response import success
from app.core.exceptions import BusinessException
from app.core.upload_validation import MAX_VIDEO_SIZE, validate_upload, detect_content_type, get_upload_max_size
from app.core.svg_sanitizer import sanitize_svg
from app.db.session import get_db
from app.schemas.common import AuthUser
from app.services.file_service import (
    _get_adapter,
    create_stored_file_record,
    generate_object_key,
    get_active_storage_provider,
)
from app.services.storage_service import StoredObject

router = APIRouter(tags=["upload"])
UPLOAD_CHUNK_SIZE = 1024 * 1024
UPLOAD_HEADER_SIZE = 4096
UPLOAD_DISK_RESERVE_BYTES = 2 * 1024 * 1024 * 1024
_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
_video_upload_in_progress = False


def _is_video_upload(filename: str) -> bool:
    return Path(filename).suffix.lower() in _VIDEO_EXTENSIONS


def _get_local_upload_free_bytes() -> int:
    return shutil.disk_usage(settings.local_upload_dir).free


async def _guard_large_video_upload(
    file: UploadFile = File(...),
    expected_size: int | None = Form(None),
):
    """在单 worker 环境中保护本地大视频上传的磁盘余量和并发。"""
    global _video_upload_in_progress

    if not file.filename or not _is_video_upload(file.filename):
        yield
        return

    if expected_size is not None:
        if expected_size < 0:
            raise BusinessException(400, "文件大小参数无效")
        if expected_size > MAX_VIDEO_SIZE:
            raise BusinessException(400, "视频文件大小超过 1GiB 限制")
        if settings.storage_backend == "local":
            required_free_bytes = expected_size + UPLOAD_DISK_RESERVE_BYTES
            if _get_local_upload_free_bytes() < required_free_bytes:
                raise BusinessException(400, "服务器可用磁盘空间不足，暂时无法接收该视频")

    if _video_upload_in_progress:
        raise BusinessException(429, "已有视频正在上传，请等待完成后再试")

    _video_upload_in_progress = True
    try:
        yield
    finally:
        _video_upload_in_progress = False


async def _save_local_upload_stream(file: UploadFile, object_key: str, content_type: str) -> tuple[StoredObject, int, str, bytes]:
    """分块保存本地上传文件，避免把完整文件读入内存。"""
    adapter = _get_adapter("local")
    max_size = get_upload_max_size(file.filename or "")
    total_size = 0
    header = b""
    sha256 = hashlib.sha256()

    try:
        with adapter.open_write_stream(object_key=object_key) as target:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_size:
                    raise BusinessException(400, f"文件大小超过限制 ({max_size / (1024 * 1024):.0f}MB)")
                if len(header) < UPLOAD_HEADER_SIZE:
                    header += chunk[:UPLOAD_HEADER_SIZE - len(header)]
                sha256.update(chunk)
                target.write(chunk)
    except Exception:
        adapter.delete(object_key=object_key)
        raise

    stored = StoredObject(
        storage_provider="local",
        bucket_name="",
        object_key=object_key,
        stored_name=Path(object_key).name,
        content_type=content_type,
        size_bytes=total_size,
    )
    return stored, total_size, sha256.hexdigest(), header


async def _spool_upload_to_temp_file(file: UploadFile):
    """分块写入临时文件，供 S3 等远端存储继续流式上传。"""
    max_size = get_upload_max_size(file.filename or "")
    total_size = 0
    header = b""
    sha256 = hashlib.sha256()
    temp_file = tempfile.TemporaryFile()

    try:
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size:
                raise BusinessException(400, f"文件大小超过限制 ({max_size / (1024 * 1024):.0f}MB)")
            if len(header) < UPLOAD_HEADER_SIZE:
                header += chunk[:UPLOAD_HEADER_SIZE - len(header)]
            sha256.update(chunk)
            temp_file.write(chunk)
        temp_file.seek(0)
        return temp_file, total_size, sha256.hexdigest(), header
    except Exception:
        temp_file.close()
        raise


@router.post("/upload", summary="文件上传", description="上传图片、文档、视频或压缩包文件，返回访问 URL")
async def upload_file(
    file: UploadFile = File(...),
    biz_type: str = Form("upload"),
    _video_upload_guard=Depends(_guard_large_video_upload),
    current_user: AuthUser = Depends(get_current_user),
    db=Depends(get_db),
):
    if not file.filename:
        raise BusinessException(400, "未选择文件")

    object_key = generate_object_key(file.filename)
    file_size = 0
    sha256_hash = ""

    if settings.storage_backend == "local":
        err = validate_upload(file.filename, 0)
        if err:
            raise BusinessException(400, err)

        stored, file_size, sha256_hash, header = await _save_local_upload_stream(file, object_key, "")
        err = validate_upload(file.filename, file_size, content=header)
        if err:
            _get_adapter("local").delete(object_key=object_key)
            raise BusinessException(400, err)

        content_type = detect_content_type(header, file.filename)

        # SVG 安全清洗需要完整 XML 文本，先流式落盘再读取清洗并覆盖。
        if Path(file.filename).suffix.lower() == ".svg":
            adapter = _get_adapter("local")
            try:
                with adapter.open_stream(object_key=object_key) as source:
                    svg_text = source.read().decode("utf-8")
            except UnicodeDecodeError:
                adapter.delete(object_key=object_key)
                raise BusinessException(400, "SVG 文件编码无效，仅支持 UTF-8")

            cleaned = sanitize_svg(svg_text)
            if not cleaned:
                adapter.delete(object_key=object_key)
                raise BusinessException(400, "SVG 文件内容不安全或为空")
            cleaned_content = cleaned.encode("utf-8")
            with adapter.open_write_stream(object_key=object_key) as target:
                target.write(cleaned_content)
            file_size = len(cleaned_content)
            sha256_hash = hashlib.sha256(cleaned_content).hexdigest()

        stored.content_type = content_type
        stored.size_bytes = file_size
    else:
        err = validate_upload(file.filename, 0)
        if err:
            raise BusinessException(400, err)

        temp_file, file_size, sha256_hash, header = await _spool_upload_to_temp_file(file)
        try:
            err = validate_upload(file.filename, file_size, content=header)
            if err:
                raise BusinessException(400, err)

            content_type = detect_content_type(header, file.filename)

            # SVG 安全清洗需要完整 XML 文本，先写入临时文件再读取清洗并覆盖。
            if Path(file.filename).suffix.lower() == ".svg":
                try:
                    temp_file.seek(0)
                    svg_text = temp_file.read().decode("utf-8")
                except UnicodeDecodeError:
                    raise BusinessException(400, "SVG 文件编码无效，仅支持 UTF-8")
                cleaned = sanitize_svg(svg_text)
                if not cleaned:
                    raise BusinessException(400, "SVG 文件内容不安全或为空")
                cleaned_content = cleaned.encode("utf-8")
                temp_file.seek(0)
                temp_file.truncate(0)
                temp_file.write(cleaned_content)
                temp_file.seek(0)
                file_size = len(cleaned_content)
                sha256_hash = hashlib.sha256(cleaned_content).hexdigest()

            adapter = _get_adapter()
            stored = adapter.save_fileobj(
                fileobj=temp_file,
                object_key=object_key,
                content_type=content_type,
                size_bytes=file_size,
            )
        finally:
            temp_file.close()

    stored_file = create_stored_file_record(
        db,
        biz_type=biz_type,
        original_name=file.filename,
        content_type=content_type,
        size_bytes=file_size,
        stored=stored,
        created_by=current_user.id,
        sha256=sha256_hash,
    )
    db.commit()

    return success({
        "file_id": stored_file.id,
        "url": f"/api/files/{stored_file.id}",
        "filename": file.filename,
        "size": file_size,
        "content_type": content_type,
        "storage_provider": get_active_storage_provider(),
    })
