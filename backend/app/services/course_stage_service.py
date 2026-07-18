"""课程阶段/目录服务。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.timezone_utils import to_beijing_iso
from app.models.entities import Course, CourseStage


def list_stages_for_course(db: Session, course_id: int, teacher_id: str | None = None):
    """获取某课程下的所有阶段（含阶段下的资料）。"""
    query = db.query(Course).filter(Course.id == course_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    course = query.first()
    if not course:
        return None
    stages = (
        db.query(CourseStage)
        .filter(CourseStage.course_id == course_id)
        .order_by(CourseStage.sort_order, CourseStage.id)
        .all()
    )
    return stages


def create_stage(
    db: Session,
    course_id: int,
    name: str,
    sort_order: int = 0,
    teacher_id: str | None = None,
):
    """为课程创建新阶段。"""
    query = db.query(Course).filter(Course.id == course_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    course = query.first()
    if not course:
        raise BusinessException(404, "课程不存在")
    # 避免同课程下同名阶段
    existing = db.query(CourseStage).filter(
        CourseStage.course_id == course_id,
        CourseStage.name == name,
    ).first()
    if existing:
        raise BusinessException(400, "该课程下已存在同名阶段")
    stage = CourseStage(
        course_id=course_id,
        name=name,
        sort_order=sort_order,
    )
    db.add(stage)
    db.flush()
    db.refresh(stage)
    return stage


def update_stage(
    db: Session,
    stage_id: int,
    name: str | None = None,
    sort_order: int | None = None,
    teacher_id: str | None = None,
):
    """更新阶段名称或排序。"""
    query = db.query(CourseStage).join(Course, Course.id == CourseStage.course_id).filter(CourseStage.id == stage_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    stage = query.first()
    if not stage:
        return None
    if name is not None:
        duplicate = db.query(CourseStage).filter(
            CourseStage.course_id == stage.course_id,
            CourseStage.name == name,
            CourseStage.id != stage_id,
        ).first()
        if duplicate:
            raise BusinessException(400, "该课程下已存在同名阶段")
        stage.name = name
    if sort_order is not None:
        stage.sort_order = sort_order
    db.flush()
    db.refresh(stage)
    return stage


def delete_stage(
    db: Session,
    stage_id: int,
    teacher_id: str | None = None,
    *,
    cascade_materials: bool = False,
    operator_id: str | None = None,
    operator_role: str = "teacher",
):
    """删除阶段。

    仅统计活跃资料（deleted_at 为空）。
    cascade_materials=False：有活跃资料时拒绝删除。
    cascade_materials=True：先软删阶段下全部活跃资料，再删除阶段行。
    """
    from app.schemas.common import AuthUser
    from app.services.soft_delete_service import soft_delete

    query = db.query(CourseStage).join(Course, Course.id == CourseStage.course_id).filter(CourseStage.id == stage_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    stage = query.first()
    if not stage:
        return False

    active_materials = [
        m for m in (stage.materials or [])
        if getattr(m, "deleted_at", None) is None
    ]
    if active_materials and not cascade_materials:
        raise BusinessException(400, "阶段下仍有资料，请先移出或删除资料，或确认级联删除")

    if active_materials and cascade_materials:
        op_id = operator_id or teacher_id or ""
        operator = AuthUser(id=op_id, name="", role=operator_role)
        for material in list(active_materials):
            # 先软删并写入 deleted_stage_* 快照；勿再清空 stage_id，
            # 以免干扰快照；物理删阶段时由 FK ON DELETE SET NULL 脱钩。
            soft_delete(db, material, operator, action="material.delete")

    db.delete(stage)
    db.flush()
    return True


def format_stage_out(stage: CourseStage):
    return {
        "id": stage.id,
        "course_id": stage.course_id,
        "source_stage_id": stage.source_stage_id,
        "name": stage.name,
        "sort_order": stage.sort_order,
        "created_at": to_beijing_iso(stage.created_at),
    }
