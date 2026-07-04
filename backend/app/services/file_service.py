"""文件元数据服务：统一管理 StoredFile 记录与存储适配器分发"""
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.models.entities import (
    Class,
    Course,
    Material,
    MaterialPreview,
    Project,
    ProjectImage,
    ShowcaseItem,
    ShowcaseItemImage,
    StoredFile,
    StudentClassEnrollment,
)
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


def _teacher_can_review_project(db: Session, teacher_id: str, project: Project) -> bool:
    """判断教师是否拥有该作品的审核范围。"""
    if project.course_id is not None:
        return db.query(Course.id).filter(
            Course.id == project.course_id,
            Course.created_by == teacher_id,
        ).first() is not None

    return db.query(StudentClassEnrollment.id).join(
        Class,
        Class.id == StudentClassEnrollment.class_id,
    ).filter(
        StudentClassEnrollment.user_id == project.author_id,
        Class.created_by == teacher_id,
    ).first() is not None


def _can_read_project_file(db: Session, file_id: int, user_id: str, role: str) -> bool:
    projects = db.query(Project).filter(
        (Project.report_file_id == file_id) | (Project.cover_file_id == file_id)
    ).all()
    image_project_ids = [
        row[0]
        for row in db.query(ProjectImage.project_id).filter(ProjectImage.file_id == file_id).all()
    ]
    if image_project_ids:
        projects.extend(db.query(Project).filter(Project.id.in_(image_project_ids)).all())

    for project in projects:
        if project.author_id == user_id:
            return True
        if project.status == "approved":
            return True
        if role == "teacher" and _teacher_can_review_project(db, user_id, project):
            return True
    return False


def _can_read_showcase_file(db: Session, file_id: int, user_id: str | None = None, role: str = "") -> bool:
    cover_exists = db.query(ShowcaseItem.id).filter(
        ShowcaseItem.cover_file_id == file_id,
        ShowcaseItem.is_active.is_(True),
    ).first() is not None
    if cover_exists:
        return True

    image_exists = db.query(ShowcaseItemImage.id).join(
        ShowcaseItem,
        ShowcaseItem.id == ShowcaseItemImage.showcase_item_id,
    ).filter(
        ShowcaseItemImage.file_id == file_id,
        ShowcaseItem.is_active.is_(True),
    ).first() is not None
    if image_exists:
        return True

    if user_id and role in {"admin", "teacher"}:
        return db.query(ShowcaseItem.id).filter(
            ShowcaseItem.cover_file_id == file_id,
            ShowcaseItem.created_by == user_id,
        ).first() is not None
    return False


def _can_read_material_preview_file(db: Session, file_id: int, user_id: str, role: str) -> bool:
    from app.services.material_service import can_view_course_materials

    preview = db.query(MaterialPreview).filter(MaterialPreview.cover_file_id == file_id).first()
    if not preview:
        return False
    material = db.query(Material).filter(Material.id == preview.material_id).first()
    if not material:
        return False
    return can_view_course_materials(db, material.course_id, user_id, role)


def can_anonymous_read_file(db: Session, record: StoredFile) -> bool:
    """匿名用户仅可读取明确公开的衍生展示图片。"""
    if _can_read_showcase_file(db, record.id):
        return True
    return db.query(MaterialPreview.id).join(
        Material,
        Material.id == MaterialPreview.material_id,
    ).join(
        Course,
        Course.id == Material.course_id,
    ).filter(
        MaterialPreview.cover_file_id == record.id,
        Course.is_public.is_(True),
    ).first() is not None


def can_current_user_read_file(db: Session, record: StoredFile, current_user) -> bool:
    """按现有业务关系判断当前用户是否可读取 StoredFile。"""
    if current_user.role == "admin":
        return True
    if record.created_by == current_user.id:
        return True

    from app.services.material_service import can_view_course_materials

    materials = db.query(Material).filter(Material.file_id == record.id).all()
    if any(
        can_view_course_materials(db, material.course_id, current_user.id, current_user.role)
        for material in materials
    ):
        return True

    if _can_read_material_preview_file(db, record.id, current_user.id, current_user.role):
        return True

    if _can_read_project_file(db, record.id, current_user.id, current_user.role):
        return True

    if _can_read_showcase_file(db, record.id, current_user.id, current_user.role):
        return True

    return False


def resolve_file_stream(
    db: Session,
    file_id: int,
    current_user=None,
    enforce_auth: bool = False,
) -> tuple[StoredFile, BinaryIO]:
    """根据 file_id 获取文件记录和文件流。找不到返回 (None, None)"""
    record = db.query(StoredFile).filter(StoredFile.id == file_id).first()
    if record is None:
        return None, None

    if enforce_auth:
        if current_user is None:
            if not can_anonymous_read_file(db, record):
                raise BusinessException(401, "无效的认证凭据")
        elif not can_current_user_read_file(db, record, current_user):
            raise BusinessException(404, "文件不存在")

    if record.storage_provider == "local":
        try:
            object_key = normalize_local_object_key(record.object_key)
        except ValueError:
            raise BusinessException(400, "文件路径不合法")
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


def normalize_local_object_key(object_key: str) -> str:
    """规范化本地 object_key，禁止目录穿越。"""
    cleaned = object_key.replace("\\", "/").lstrip("/")
    if cleaned.startswith("uploads/"):
        cleaned = cleaned[len("uploads/"):]
    parts = [part for part in cleaned.split("/") if part]
    if any(part == ".." for part in parts):
        raise ValueError("文件路径不合法")
    return "/".join(parts)


def build_x_accel_redirect_path(object_key: str) -> str:
    """构建 Nginx 内部跳转路径。"""
    safe_key = normalize_local_object_key(object_key)
    return f"/_protected_uploads/{safe_key}"
