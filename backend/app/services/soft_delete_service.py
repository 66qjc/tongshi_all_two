"""软删除与回收站服务。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.timezone_utils import to_beijing_iso
from app.models.entities import Announcement, Class, Course, Material, Project, Question, User
from app.schemas.common import AuthUser
from app.services.audit_service import create_audit_log

RESOURCE_MODELS = {
    "users": User,
    "courses": Course,
    "classes": Class,
    "announcements": Announcement,
    "projects": Project,
    "materials": Material,
    "questions": Question,
}

RESOURCE_ACTION_NAMES = {
    "users": "user",
    "courses": "course",
    "classes": "class",
    "announcements": "announcement",
    "projects": "project",
    "materials": "material",
    "questions": "question",
}


def now_utc() -> datetime:
    """返回 UTC 当前时间。"""
    return datetime.now(timezone.utc)


def filter_active(query, model):
    """过滤未软删除数据。"""
    if hasattr(model, "deleted_at"):
        return query.filter(model.deleted_at.is_(None))
    return query


def _resource_name(item: Any) -> str:
    for attr in ["name", "title", "stem", "id"]:
        if hasattr(item, attr):
            value = getattr(item, attr)
            if value is not None:
                return str(value)[:256]
    return ""


def _format_deleted(item: Any) -> dict:
    return {
        "id": item.id,
        "name": _resource_name(item),
        "deleted_at": to_beijing_iso(getattr(item, "deleted_at", None)),
        "deleted_by": getattr(item, "deleted_by", None),
    }


def list_deleted_resources(db: Session, resource_type: str, page: int = 1, page_size: int = 20) -> dict:
    """列出指定资源类型的已删除数据。"""
    model = RESOURCE_MODELS.get(resource_type)
    if model is None:
        raise BusinessException(404, "资源类型不存在")
    safe_page = max(page or 1, 1)
    safe_page_size = max(min(page_size or 20, 100), 1)
    query = db.query(model).filter(model.deleted_at.isnot(None))
    total = query.count()
    items = query.order_by(model.deleted_at.desc(), model.id.desc()).offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()
    return {"items": [_format_deleted(item) for item in items], "total": total, "page": safe_page, "page_size": safe_page_size}


def soft_delete(db: Session, item: Any, operator: AuthUser, *, cascade: bool = True, action: str | None = None) -> Any:
    """软删除单个对象，并按课程级联软删除核心子资源。"""
    if not hasattr(item, "deleted_at"):
        raise BusinessException(400, "该资源不支持软删除")
    if item.deleted_at is None:
        item.deleted_at = now_utc()
        item.deleted_by = operator.id
    details: dict[str, Any] = {}
    if cascade and isinstance(item, Course):
        child_specs = [
            (Class, Class.course_id == item.id),
            (Material, Material.course_id == item.id),
            (Announcement, Announcement.course_id == item.id),
        ]
        for model, criterion in child_specs:
            rows = db.query(model).filter(criterion, model.deleted_at.is_(None)).all()
            details[model.__tablename__] = len(rows)
            for row in rows:
                row.deleted_at = item.deleted_at
                row.deleted_by = operator.id
    resource_type = getattr(item, "__tablename__", None)
    create_audit_log(
        db,
        user=operator,
        action=action or f"{RESOURCE_ACTION_NAMES.get(resource_type, resource_type)}.delete",
        resource_type=resource_type,
        resource_id=item.id,
        resource_name=_resource_name(item),
        details=details,
    )
    db.flush()
    return item


def restore_resource(db: Session, resource_type: str, resource_id: int, operator: AuthUser) -> dict:
    """恢复已软删除资源。"""
    model = RESOURCE_MODELS.get(resource_type)
    if model is None:
        raise BusinessException(404, "资源类型不存在")
    item = db.query(model).filter(model.id == resource_id).first()
    if not item or item.deleted_at is None:
        raise BusinessException(404, "已删除资源不存在")
    deleted_at = item.deleted_at
    deleted_by = item.deleted_by
    item.deleted_at = None
    item.deleted_by = None
    restored_children: dict[str, int] = {}
    if isinstance(item, Course):
        child_specs = [
            (Class, Class.course_id == item.id),
            (Material, Material.course_id == item.id),
            (Announcement, Announcement.course_id == item.id),
        ]
        for child_model, criterion in child_specs:
            rows = db.query(child_model).filter(
                criterion,
                child_model.deleted_at == deleted_at,
                child_model.deleted_by == deleted_by,
            ).all()
            restored_children[child_model.__tablename__] = len(rows)
            for row in rows:
                row.deleted_at = None
                row.deleted_by = None
    create_audit_log(
        db,
        user=operator,
        action=f"{RESOURCE_ACTION_NAMES.get(resource_type, resource_type)}.restore",
        resource_type=resource_type,
        resource_id=item.id,
        resource_name=_resource_name(item),
        details={"restored_children": restored_children} if restored_children else {},
    )
    db.commit()
    return _format_deleted(item)


def purge_resource(db: Session, resource_type: str, resource_id: int, operator: AuthUser) -> dict:
    """彻底删除已软删除资源。"""
    model = RESOURCE_MODELS.get(resource_type)
    if model is None:
        raise BusinessException(404, "资源类型不存在")
    item = db.query(model).filter(model.id == resource_id, model.deleted_at.isnot(None)).first()
    if not item:
        raise BusinessException(404, "已删除资源不存在")
    name = _resource_name(item)
    db.delete(item)
    create_audit_log(
        db,
        user=operator,
        action=f"{RESOURCE_ACTION_NAMES.get(resource_type, resource_type)}.purge",
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=name,
    )
    db.commit()
    return {"id": resource_id}
