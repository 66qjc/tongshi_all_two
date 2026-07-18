"""软删除与回收站服务。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, cast
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.timezone_utils import to_beijing_iso
from app.models.entities import Announcement, Class, Course, CourseStage, Material, Project, Question, User
from app.schemas.common import AuthUser
from app.services.audit_service import create_audit_log
from app.services.soft_delete_policy import get_resource_policy

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

RESOURCE_DISPLAY_NAMES = {
    "classes": "班级",
    "materials": "资料",
    "announcements": "作业",
}

COURSE_CHILD_MODELS = {
    "classes": (Class, Class.course_id),
    "materials": (Material, Material.course_id),
    "announcements": (Announcement, Announcement.course_id),
}


def now_utc() -> datetime:
    """返回 UTC 当前时间。"""
    return datetime.now(timezone.utc)


def filter_active(query, model):
    """过滤未软删除数据。"""
    if hasattr(model, "deleted_at"):
        return query.filter(model.deleted_at.is_(None))
    return query


def _coerce_resource_id(model, resource_id: str) -> Any:
    """按资源主键类型转换路径参数，拒绝错误格式。"""
    raw_id = str(resource_id).strip() if resource_id is not None else ""
    if not raw_id:
        raise BusinessException(400, "资源 ID 格式不正确")
    try:
        python_type = inspect(model).primary_key[0].type.python_type
        return raw_id if python_type is str else python_type(raw_id)
    except (TypeError, ValueError, AttributeError):
        raise BusinessException(400, "资源 ID 格式不正确")


def _resource_name(item: Any) -> str:
    for attr in ["name", "title", "stem", "id"]:
        if hasattr(item, attr):
            value = getattr(item, attr)
            if value is not None:
                return str(value)[:256]
    return ""


def _format_deleted(item: Any) -> dict:
    data = {
        "id": item.id,
        "name": _resource_name(item),
        "deleted_at": to_beijing_iso(getattr(item, "deleted_at", None)),
        "deleted_by": getattr(item, "deleted_by", None),
    }
    if isinstance(item, Material):
        data["course_id"] = item.course_id
        data["needs_target_course"] = item.course_id is None
    return data


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


def soft_delete(db: Session, item: Any, operator: AuthUser, *, cascade: bool = False, action: str | None = None) -> Any:
    """软删除单个对象；仅课程依固定策略级联同批子资源。"""
    if not hasattr(item, "deleted_at"):
        raise BusinessException(400, "该资源不支持软删除")
    was_active = item.deleted_at is None
    if isinstance(item, Question) and was_active:
        active_assignment_question_ids = db.query(
            cast(Announcement.question_ids, String),
        ).filter(
            Announcement.deleted_at.is_(None),
        ).all()
        for (raw_question_ids,) in active_assignment_question_ids:
            try:
                question_ids = json.loads(raw_question_ids)
            except (TypeError, json.JSONDecodeError):
                raise BusinessException(400, "作业题目数据格式异常，不能删除题目")
            if not isinstance(question_ids, list) or any(
                not isinstance(question_id, int) or isinstance(question_id, bool)
                for question_id in question_ids
            ):
                raise BusinessException(400, "作业题目数据格式异常，不能删除题目")
            if item.id in question_ids:
                raise BusinessException(400, "题目已被未删除作业使用，不能删除")
    if was_active:
        # 资料软删时写入所属阶段快照，便于后续原位恢复
        if isinstance(item, Material):
            stage = None
            if getattr(item, "stage_id", None) is not None:
                stage = db.query(CourseStage).filter(CourseStage.id == item.stage_id).first()
            if stage is not None:
                item.deleted_stage_id = stage.id
                item.deleted_stage_name = stage.name
                item.deleted_stage_sort_order = stage.sort_order
            else:
                item.deleted_stage_id = None
                item.deleted_stage_name = None
                item.deleted_stage_sort_order = None
        deleted_at = now_utc()
        item.deleted_at = deleted_at
        item.deleted_by = operator.id
    details: dict[str, Any] = {"删除方式": "软删除"}
    if isinstance(item, Course) and was_active:
        child_counts: dict[str, int] = {}
        for child_type in get_resource_policy("courses").cascade_children:
            model, course_id_column = COURSE_CHILD_MODELS[child_type]
            rows = db.query(model).filter(
                course_id_column == item.id,
                model.deleted_at.is_(None),
            ).all()
            child_counts[RESOURCE_DISPLAY_NAMES[child_type]] = len(rows)
            for row in rows:
                row.deleted_at = item.deleted_at
                row.deleted_by = operator.id
        details["级联删除子资源"] = child_counts
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


def _resolve_material_stage_on_restore(db: Session, item: Material, target_course_id: int) -> dict[str, Any]:
    """按当前 stage 或删除快照，将资料挂回目标课程下的阶段。"""
    info: dict[str, Any] = {"阶段处理": "无快照", "重建阶段": False}
    # 1) 当前 stage_id 仍有效且属于目标课程
    if item.stage_id is not None:
        stage = (
            db.query(CourseStage)
            .filter(CourseStage.id == item.stage_id, CourseStage.course_id == target_course_id)
            .first()
        )
        if stage is not None:
            info["阶段处理"] = "保留原阶段"
            info["阶段ID"] = stage.id
            info["阶段名称"] = stage.name
            return info
        item.stage_id = None

    name = (item.deleted_stage_name or "").strip()
    if not name:
        info["阶段处理"] = "无阶段快照"
        item.stage_id = None
        return info

    existing = (
        db.query(CourseStage)
        .filter(CourseStage.course_id == target_course_id, CourseStage.name == name)
        .first()
    )
    if existing is not None:
        item.stage_id = existing.id
        info["阶段处理"] = "复用同名阶段"
        info["阶段ID"] = existing.id
        info["阶段名称"] = existing.name
        return info

    sort_order = item.deleted_stage_sort_order
    if sort_order is None:
        sort_order = 0
    stage = CourseStage(
        course_id=target_course_id,
        name=name,
        sort_order=sort_order,
    )
    db.add(stage)
    db.flush()
    item.stage_id = stage.id
    info["阶段处理"] = "重建同名阶段"
    info["重建阶段"] = True
    info["阶段ID"] = stage.id
    info["阶段名称"] = stage.name
    return info


def restore_resource(
    db: Session,
    resource_type: str,
    resource_id: str,
    operator: AuthUser,
    target_course_id: int | None = None,
) -> dict:
    """恢复已软删除资源。

    资料在课程物理清理后 course_id 为空：必须指定活跃 target_course_id 才能恢复。
    """
    model = RESOURCE_MODELS.get(resource_type)
    if model is None:
        raise BusinessException(404, "资源类型不存在")
    coerced_id = _coerce_resource_id(model, resource_id)
    item = db.query(model).filter(model.id == coerced_id).first()
    if not item or item.deleted_at is None:
        raise BusinessException(404, "已删除资源不存在")
    deleted_at = item.deleted_at
    deleted_by = item.deleted_by

    remount_course_id = None
    if isinstance(item, Material) and item.course_id is None:
        if not target_course_id:
            raise BusinessException(400, "原课程已清理，请选择恢复到的课程")
        target = (
            db.query(Course)
            .filter(Course.id == target_course_id, Course.deleted_at.is_(None))
            .first()
        )
        if not target:
            raise BusinessException(400, "目标课程不存在或已删除")
        item.course_id = target.id
        remount_course_id = target.id

    # 资料恢复：挂回/重建阶段并清空删除快照，再清除 deleted 标记
    stage_restore_info: dict[str, Any] = {}
    if isinstance(item, Material):
        target_cid = item.course_id
        if target_cid is None:
            raise BusinessException(400, "原课程已清理，请选择恢复到的课程")
        stage_restore_info = _resolve_material_stage_on_restore(db, item, target_cid)
        item.deleted_stage_id = None
        item.deleted_stage_name = None
        item.deleted_stage_sort_order = None

    item.deleted_at = None
    item.deleted_by = None
    restored_children: dict[str, int] = {}
    if isinstance(item, Course) and get_resource_policy(resource_type).restore_mode == "same_batch":
        for child_type in get_resource_policy(resource_type).cascade_children:
            child_model, course_id_column = COURSE_CHILD_MODELS[child_type]
            rows = db.query(child_model).filter(
                course_id_column == item.id,
                child_model.deleted_at == deleted_at,
                child_model.deleted_by == deleted_by,
            ).all()
            restored_children[RESOURCE_DISPLAY_NAMES[child_type]] = len(rows)
            for row in rows:
                row.deleted_at = None
                row.deleted_by = None
    restored_child_count = sum(restored_children.values())
    details: dict[str, Any] = {
        "恢复子资源数量": restored_child_count,
        "恢复子资源明细": restored_children,
    }
    if remount_course_id is not None:
        details["重新挂载课程ID"] = remount_course_id
    if stage_restore_info:
        details.update(stage_restore_info)
    create_audit_log(
        db,
        user=operator,
        action=f"{RESOURCE_ACTION_NAMES.get(resource_type, resource_type)}.restore",
        resource_type=resource_type,
        resource_id=item.id,
        resource_name=_resource_name(item),
        details=details,
    )
    db.commit()
    result = _format_deleted(item)
    result["恢复子资源数量"] = restored_child_count
    if remount_course_id is not None:
        result["重新挂载课程ID"] = remount_course_id
    if stage_restore_info:
        result.update(stage_restore_info)
    return result


def purge_resource(db: Session, resource_type: str, resource_id: str, operator: AuthUser) -> dict:
    """公开清除入口在保留期内固定拒绝。"""
    raise BusinessException(403, "资源仍在保留期，不能提前彻底删除")
