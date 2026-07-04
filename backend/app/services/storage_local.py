"""本地文件存储适配器"""
from pathlib import Path
from typing import BinaryIO

from app.services.storage_service import StoredObject


class LocalStorageAdapter:
    """本地文件系统存储适配器，兼容历史 /uploads 目录"""

    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, object_key: str) -> Path:
        """解析本地文件路径并确保结果仍位于上传根目录内。"""
        cleaned = object_key.replace("\\", "/").lstrip("/")
        if cleaned.startswith("uploads/"):
            cleaned = cleaned[len("uploads/"):]
        target = (self.root_dir / cleaned).resolve()
        root = self.root_dir.resolve()
        if target != root and root not in target.parents:
            raise ValueError("文件路径不合法")
        return target

    def save_bytes(self, *, content: bytes, object_key: str, content_type: str = "") -> StoredObject:
        file_path = self._resolve_safe_path(object_key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return StoredObject(
            storage_provider="local",
            bucket_name="",
            object_key=object_key,
            stored_name=object_key,
            content_type=content_type,
            size_bytes=len(content),
        )

    def open_write_stream(self, *, object_key: str) -> BinaryIO:
        file_path = self._resolve_safe_path(object_key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return open(file_path, "wb")

    def save_fileobj(
        self,
        *,
        fileobj: BinaryIO,
        object_key: str,
        content_type: str = "",
        bucket_name: str = "",
        size_bytes: int = 0,
    ) -> StoredObject:
        total_size = 0
        with self.open_write_stream(object_key=object_key) as target:
            while True:
                chunk = fileobj.read(1024 * 1024)
                if not chunk:
                    break
                total_size += len(chunk)
                target.write(chunk)
        return StoredObject(
            storage_provider="local",
            bucket_name=bucket_name,
            object_key=object_key,
            stored_name=object_key,
            content_type=content_type,
            size_bytes=size_bytes or total_size,
        )

    def open_stream(self, *, object_key: str) -> BinaryIO:
        file_path = self._resolve_safe_path(object_key)
        return open(file_path, "rb")

    def exists(self, *, object_key: str) -> bool:
        return self._resolve_safe_path(object_key).is_file()

    def delete(self, *, object_key: str) -> None:
        file_path = self._resolve_safe_path(object_key)
        if file_path.is_file():
            file_path.unlink()
