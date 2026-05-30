"""文件元数据服务：统一管理 StoredFile 记录与存储适配器分发"""
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import StoredFile
from app.services.storage_local import LocalStorageAdapter
from app.services.storage_service import StoredObject

# 全局本地适配器实例（始终可用，兼容历史文件）
_local_adapter = LocalStorageAdapter(settings.local_upload_dir)

# S3 适配器延迟初始化
_s3_adapter = None


def _get_adapter(storage_provider: str = ""):
    """根据配置或指定 provider 返回适配器"""
    provider = storage_provider or settings.storage_backend
    if provider == "s3":
        global _s3_adapter
        if _s3_adapter is None:
            from app.services.storage_s3 import S3StorageAdapter
            _s3_adapter = S3StorageAdapter()
        return _s3_adapter
    return _local_adapter


def get_active_storage_provider() -> str:
    """返回当前活跃的存储后端名称"""
    return settings.storage_backend


def create_stored_file_record(
    db: Session,
    *,
    biz_type: str,
    original_name: str,
    content_type: str,
    size_bytes: int,
    stored: StoredObject,
    created_by: str,
    biz_id: int | None = None,
    sha256: str = "",
) -> StoredFile:
    """创建 StoredFile 数据库记录"""
    ext = Path(original_name).suffix.lower()
    stored_name = Path(stored.object_key).name

    record = StoredFile(
        biz_type=biz_type,
        biz_id=biz_id,
        storage_provider=stored.storage_provider,
        bucket_name=stored.bucket_name,
        object_key=stored.object_key,
        original_name=original_name,
        stored_name=stored_name,
        content_type=content_type,
        extension=ext,
        size_bytes=size_bytes,
        sha256=sha256,
        status="active",
        created_by=created_by,
    )
    db.add(record)
    db.flush()
    return record


def build_file_url(file_id: int) -> str:
    """构建统一文件访问 URL"""
    return f"/api/files/{file_id}"


def resolve_file_stream(db: Session, file_id: int) -> tuple[StoredFile, BinaryIO]:
    """根据 file_id 获取文件记录和文件流。找不到返回 (None, None)"""
    record = db.query(StoredFile).filter(StoredFile.id == file_id).first()
    if record is None:
        return None, None

    if record.storage_provider == "local":
        # 本地文件：object_key 可能是完整路径或相对路径
        object_key = record.object_key
        # 兼容历史：如果 object_key 以 /uploads/ 开头，去掉前缀
        if object_key.startswith("/uploads/"):
            object_key = object_key[len("/uploads/"):]
        adapter = _local_adapter
    else:
        adapter = _get_adapter(record.storage_provider)
        object_key = record.object_key

    if not adapter.exists(object_key=object_key):
        return record, None

    try:
        stream = adapter.open_stream(object_key=object_key)
    except FileNotFoundError:
        return record, None
    except Exception:
        return record, None

    return record, stream


def generate_object_key(filename: str) -> str:
    """生成唯一的 object key"""
    ext = Path(filename).suffix.lower()
    return f"{uuid.uuid4().hex[:12]}{ext}"
