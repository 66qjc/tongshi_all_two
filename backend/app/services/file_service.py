"""文件元数据服务：统一管理 StoredFile 记录与存储适配器分发"""
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import or_
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


def _can_view_active_course_materials(
    db: Session,
    course_id: int,
    user_id: str,
    role: str,
) -> bool:
    """只基于未删除课程和班级判断资料访问权限。"""
    if role == "student":
        return db.query(StudentClassEnrollment.id).join(
            Class,
            Class.id == StudentClassEnrollment.class_id,
        ).join(
            Course,
            Course.id == Class.course_id,
        ).filter(
            StudentClassEnrollment.user_id == user_id,
            Class.course_id == course_id,
            Class.deleted_at.is_(None),
            Course.deleted_at.is_(None),
        ).first() is not None

    query = db.query(Course.id).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None),
    )
    if role == "teacher":
        query = query.filter(or_(Course.created_by == user_id, Course.is_public.is_(True)))
    return query.first() is not None


def _teacher_can_review_project(db: Session, teacher_id: str, project: Project) -> bool:
    """判断教师是否拥有该作品的审核范围。"""
    if project.course_id is not None:
        return db.query(Course.id).filter(
            Course.id == project.course_id,
            Course.created_by == teacher_id,
            Course.deleted_at.is_(None),
        ).first() is not None

    return db.query(StudentClassEnrollment.id).join(
        Class,
        Class.id == StudentClassEnrollment.class_id,
    ).filter(
        StudentClassEnrollment.user_id == project.author_id,
        Class.created_by == teacher_id,
        Class.deleted_at.is_(None),
    ).first() is not None


def _can_read_project_file(db: Session, file_id: int, user_id: str, role: str) -> bool:
    projects = db.query(Project).filter(
        Project.deleted_at.is_(None),
        (Project.report_file_id == file_id) | (Project.cover_file_id == file_id),
    ).all()
    image_project_ids = [
        row[0]
        for row in db.query(ProjectImage.project_id).filter(ProjectImage.file_id == file_id).all()
    ]
    if image_project_ids:
        projects.extend(db.query(Project).filter(
            Project.id.in_(image_project_ids),
            Project.deleted_at.is_(None),
        ).all())

    for project in projects:
        if project.course_id is not None and db.query(Course.id).filter(
            Course.id == project.course_id,
            Course.deleted_at.is_(None),
        ).first() is None:
            continue
        if role == "admin":
            return True
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
        owned_cover_exists = db.query(ShowcaseItem.id).filter(
            ShowcaseItem.cover_file_id == file_id,
            ShowcaseItem.created_by == user_id,
        ).first() is not None
        if owned_cover_exists:
            return True

        owned_image_exists = db.query(ShowcaseItemImage.id).join(
            ShowcaseItem,
            ShowcaseItem.id == ShowcaseItemImage.showcase_item_id,
        ).filter(
            ShowcaseItemImage.file_id == file_id,
            ShowcaseItem.created_by == user_id,
        ).first() is not None
        if owned_image_exists:
            return True

    if _showcase_content_block_file_exists(db, file_id, active_only=True):
        return True

    if not user_id or role not in {"admin", "teacher"}:
        return False
    return _showcase_content_block_file_exists(db, file_id, owner_id=user_id)


def _content_block_file_ids(content_blocks) -> set[int]:
    """提取图文混排内容块中引用的图片文件 ID。"""
    if not isinstance(content_blocks, list):
        return set()

    file_ids = set()
    for block in content_blocks:
        if not isinstance(block, dict) or block.get("type") != "image":
            continue
        data = block.get("data")
        if not isinstance(data, dict):
            continue
        file_id = data.get("file_id")
        if isinstance(file_id, int) and file_id > 0:
            file_ids.add(file_id)
    return file_ids


def _showcase_content_block_file_exists(
    db: Session,
    file_id: int,
    *,
    active_only: bool = False,
    owner_id: str | None = None,
) -> bool:
    """判断文件是否被展示内容块引用，必要时只检查激活内容。"""
    query = db.query(
        ShowcaseItem.id,
        ShowcaseItem.created_by,
        ShowcaseItem.content_blocks,
    )
    if active_only:
        query = query.filter(ShowcaseItem.is_active.is_(True))
    if owner_id is not None:
        query = query.filter(ShowcaseItem.created_by == owner_id)
    return any(
        file_id in _content_block_file_ids(content_blocks)
        for _, _, content_blocks in query.yield_per(100)
    )


def _can_read_material_preview_file(db: Session, file_id: int, user_id: str, role: str) -> bool:
    rows = db.query(Material).join(
        MaterialPreview,
        MaterialPreview.material_id == Material.id,
    ).join(
        Course,
        Course.id == Material.course_id,
    ).filter(
        MaterialPreview.cover_file_id == file_id,
        Material.deleted_at.is_(None),
        Course.deleted_at.is_(None),
    ).all()
    return any(
        _can_view_active_course_materials(db, material.course_id, user_id, role)
        for material in rows
    )


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
        Material.deleted_at.is_(None),
        Course.deleted_at.is_(None),
    ).first() is not None


def _has_any_file_reference(db: Session, file_id: int) -> bool:
    """判断文件是否已绑定任一业务记录，包括已删除记录。"""
    checks = (
        db.query(Material.id).filter(Material.file_id == file_id),
        db.query(MaterialPreview.id).filter(MaterialPreview.cover_file_id == file_id),
        db.query(Project.id).filter(
            (Project.report_file_id == file_id) | (Project.cover_file_id == file_id),
        ),
        db.query(ProjectImage.id).filter(ProjectImage.file_id == file_id),
        db.query(ShowcaseItem.id).filter(ShowcaseItem.cover_file_id == file_id),
        db.query(ShowcaseItemImage.id).filter(ShowcaseItemImage.file_id == file_id),
    )
    if any(query.first() is not None for query in checks):
        return True
    return _showcase_content_block_file_exists(db, file_id)


def _has_active_file_reference(db: Session, file_id: int) -> bool:
    """判断文件是否仍有至少一条未删除的有效业务引用。"""
    active_material = db.query(Material.id).join(
        Course,
        Course.id == Material.course_id,
    ).filter(
        Material.file_id == file_id,
        Material.deleted_at.is_(None),
        Course.deleted_at.is_(None),
    ).first()
    if active_material:
        return True

    active_preview = db.query(MaterialPreview.id).join(
        Material,
        Material.id == MaterialPreview.material_id,
    ).join(
        Course,
        Course.id == Material.course_id,
    ).filter(
        MaterialPreview.cover_file_id == file_id,
        Material.deleted_at.is_(None),
        Course.deleted_at.is_(None),
    ).first()
    if active_preview:
        return True

    image_project_ids = db.query(ProjectImage.project_id).filter(ProjectImage.file_id == file_id)
    active_project = db.query(Project.id).outerjoin(
        Course,
        Course.id == Project.course_id,
    ).filter(
        Project.deleted_at.is_(None),
        or_(
            Project.report_file_id == file_id,
            Project.cover_file_id == file_id,
            Project.id.in_(image_project_ids),
        ),
        or_(Project.course_id.is_(None), Course.deleted_at.is_(None)),
    ).first()
    if active_project:
        return True

    active_showcase = db.query(ShowcaseItem.id).outerjoin(
        ShowcaseItemImage,
        ShowcaseItemImage.showcase_item_id == ShowcaseItem.id,
    ).filter(
        ShowcaseItem.is_active.is_(True),
        or_(
            ShowcaseItem.cover_file_id == file_id,
            ShowcaseItemImage.file_id == file_id,
        ),
    ).first() is not None
    if active_showcase:
        return True
    return _showcase_content_block_file_exists(db, file_id, active_only=True)


def can_current_user_read_file(db: Session, record: StoredFile, current_user) -> bool:
    """按现有业务关系判断当前用户是否可读取 StoredFile。"""
    has_business_reference = _has_any_file_reference(db, record.id)
    if current_user.role == "admin":
        if not has_business_reference:
            return True
        if _has_active_file_reference(db, record.id):
            return True
        return _can_read_showcase_file(db, record.id, current_user.id, current_user.role)
    if not has_business_reference:
        return record.created_by == current_user.id

    materials = db.query(Material).join(
        Course,
        Course.id == Material.course_id,
    ).filter(
        Material.file_id == record.id,
        Material.deleted_at.is_(None),
        Course.deleted_at.is_(None),
    ).all()
    if any(
        _can_view_active_course_materials(
            db,
            material.course_id,
            current_user.id,
            current_user.role,
        )
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


def get_authorized_file_record(
    db: Session,
    file_id: int,
    current_user,
    allow_anonymous: bool,
) -> StoredFile:
    """只校验文件记录和业务权限，不访问底层存储。"""
    record = db.query(StoredFile).filter(
        StoredFile.id == file_id,
        StoredFile.status == "active",
    ).first()
    if record is None:
        raise BusinessException(404, "文件不存在")

    if current_user is None:
        if allow_anonymous and can_anonymous_read_file(db, record):
            return record
        raise BusinessException(401, "无效的认证凭据")

    if not can_current_user_read_file(db, record, current_user):
        raise BusinessException(404, "文件不存在")
    return record


def resolve_file_stream(
    db: Session,
    file_id: int,
    current_user=None,
    enforce_auth: bool = False,
) -> tuple[StoredFile | None, BinaryIO | None]:
    """根据 file_id 获取文件记录和文件流。找不到返回 (None, None)"""
    if enforce_auth:
        record = get_authorized_file_record(
            db,
            file_id,
            current_user,
            allow_anonymous=True,
        )
    else:
        record = db.query(StoredFile).filter(
            StoredFile.id == file_id,
            StoredFile.status == "active",
        ).first()
        if record is None:
            return None, None

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
