"""课时管理服务。"""
from __future__ import annotations

from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.html_sanitizer import sanitize_lesson_html
from app.core.timezone_utils import to_beijing_iso
from app.models.entities import Course, CourseProgress, Lesson, LessonProgress
from app.schemas.common import AuthUser, LessonCreate, LessonReorderItem, LessonUpdate
from app.services.access_control_service import student_can_access_course


def _get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise BusinessException(404, "课程不存在")
    return course


def _require_course_manage_access(db: Session, course_id: int, current_user: AuthUser) -> Course:
    """校验当前用户对课程的管理权限。"""
    course = _get_course_or_404(db, course_id)
    if current_user.role != "admin" and course.created_by != current_user.id:
        raise BusinessException(403, "无权操作该课程")
    return course


def _require_course_read_access(db: Session, course_id: int, current_user: AuthUser) -> Course:
    """校验当前用户对课程课时的读取权限。"""
    course = _get_course_or_404(db, course_id)
    if current_user.role == "admin":
        return course
    if current_user.role == "teacher":
        if course.created_by != current_user.id:
            raise BusinessException(403, "无权查看该课程")
        return course
    if current_user.role == "student":
        if not student_can_access_course(db, current_user.id, course_id):
            raise BusinessException(404, "课程不存在")
        return course
    raise BusinessException(403, "无权查看该课程")


def _require_lesson_read_access(db: Session, lesson_id: int, current_user: AuthUser) -> Lesson:
    """校验当前用户对课时的读取权限，并返回课时对象。"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise BusinessException(404, "课时不存在")
    _require_course_read_access(db, lesson.course_id, current_user)
    if current_user.role == "student" and lesson.status != "published":
        raise BusinessException(404, "课时不存在")
    return lesson


def _require_lesson_manage_access(db: Session, lesson_id: int, current_user: AuthUser) -> Lesson:
    """校验当前用户对课时的管理权限，并返回课时对象。"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise BusinessException(404, "课时不存在")
    _require_course_manage_access(db, lesson.course_id, current_user)
    return lesson


def format_lesson_out(lesson: Lesson) -> dict:
    """将 Lesson 对象格式化为统一输出字典。"""
    return {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "content": sanitize_lesson_html(lesson.content),
        "status": lesson.status,
        "sort_order": lesson.sort_order,
        "created_at": to_beijing_iso(lesson.created_at),
        "updated_at": to_beijing_iso(lesson.updated_at),
    }


def get_lessons_by_course(db: Session, course_id: int, current_user: AuthUser) -> List[Lesson]:
    """获取课程下课时，学生只返回已发布课时。"""
    _require_course_read_access(db, course_id, current_user)
    query = db.query(Lesson).filter(Lesson.course_id == course_id)
    if current_user.role == "student":
        query = query.filter(Lesson.status == "published")
    return query.order_by(Lesson.sort_order, Lesson.id).all()


def create_lesson(
    db: Session,
    course_id: int,
    data: LessonCreate,
    current_user: AuthUser,
) -> Lesson:
    """为课程创建新课时。"""
    _require_course_manage_access(db, course_id, current_user)

    # 未显式提供有效排序值时，自动追加到末尾。
    sort_order = data.sort_order if data.sort_order > 0 else None
    if sort_order is None:
        max_order = (
            db.query(func.max(Lesson.sort_order))
            .filter(Lesson.course_id == course_id)
            .scalar()
        )
        sort_order = (max_order or 0) + 1

    lesson = Lesson(
        course_id=course_id,
        title=data.title.strip(),
        content=sanitize_lesson_html(data.content),
        status=data.status,
        sort_order=sort_order,
    )
    db.add(lesson)
    db.flush()
    db.refresh(lesson)
    return lesson


def get_lesson(db: Session, lesson_id: int, current_user: AuthUser) -> Lesson:
    """获取课时详情。"""
    return _require_lesson_read_access(db, lesson_id, current_user)


def update_lesson(
    db: Session,
    lesson_id: int,
    data: LessonUpdate,
    current_user: AuthUser,
) -> Lesson:
    """更新课时信息。"""
    lesson = _require_lesson_manage_access(db, lesson_id, current_user)

    if data.title is not None:
        lesson.title = data.title.strip()
    if data.content is not None:
        lesson.content = sanitize_lesson_html(data.content)
    if data.status is not None:
        lesson.status = data.status
    if data.sort_order is not None:
        lesson.sort_order = data.sort_order

    db.flush()
    db.refresh(lesson)
    return lesson


def delete_lesson(db: Session, lesson_id: int, current_user: AuthUser) -> bool:
    """删除课时。"""
    lesson = _require_lesson_manage_access(db, lesson_id, current_user)
    (
        db.query(CourseProgress)
        .filter(CourseProgress.last_lesson_id == lesson.id)
        .update({CourseProgress.last_lesson_id: None}, synchronize_session=False)
    )
    db.query(LessonProgress).filter(LessonProgress.lesson_id == lesson.id).delete(synchronize_session=False)
    db.delete(lesson)
    db.flush()
    return True


def reorder_lessons(
    db: Session,
    course_id: int,
    items: List[LessonReorderItem],
    current_user: AuthUser,
) -> None:
    """批量更新课程下所有课时的排序。"""
    _require_course_manage_access(db, course_id, current_user)

    if not items:
        return

    item_ids = {item.id for item in items}
    lessons = (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id, Lesson.id.in_(item_ids))
        .all()
    )
    if len(lessons) != len(item_ids):
        raise BusinessException(400, "排序请求中包含不属于该课程的课时")

    order_map = {item.id: item.sort_order for item in items}
    for lesson in lessons:
        lesson.sort_order = order_map[lesson.id]

    db.flush()
