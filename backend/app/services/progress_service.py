"""学习进度服务。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Course, CourseProgress, Lesson
from app.schemas.common import AuthUser, CourseProgressIn
from app.services.access_control_service import student_can_access_course


def _require_course_progress_access(db: Session, course_id: int, current_user: AuthUser) -> Course:
    """校验当前用户是否可以读写自己在该课程下的学习进度。"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise BusinessException(404, "课程不存在")
    if current_user.role == "admin":
        return course
    if current_user.role == "teacher":
        if course.created_by != current_user.id:
            raise BusinessException(403, "无权访问该课程进度")
        return course
    if current_user.role == "student":
        if not student_can_access_course(db, current_user.id, course_id):
            raise BusinessException(404, "课程不存在")
        return course
    raise BusinessException(403, "无权访问该课程进度")


def get_progress(db: Session, course_id: int, current_user: AuthUser) -> int | None:
    """获取当前用户在指定课程的学习进度。"""
    _require_course_progress_access(db, course_id, current_user)
    progress = (
        db.query(CourseProgress)
        .filter(
            CourseProgress.user_id == current_user.id,
            CourseProgress.course_id == course_id,
        )
        .first()
    )
    return progress.last_lesson_id if progress else None


def save_progress(
    db: Session,
    course_id: int,
    data: CourseProgressIn,
    current_user: AuthUser,
) -> int:
    """保存或更新当前用户在指定课程的学习进度。"""
    _require_course_progress_access(db, course_id, current_user)

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == data.lesson_id, Lesson.course_id == course_id)
        .first()
    )
    if not lesson:
        raise BusinessException(400, "课时不存在或不属于该课程")
    if current_user.role == "student" and lesson.status != "published":
        raise BusinessException(404, "课时不存在")

    progress = (
        db.query(CourseProgress)
        .filter(
            CourseProgress.user_id == current_user.id,
            CourseProgress.course_id == course_id,
        )
        .first()
    )

    if progress:
        progress.last_lesson_id = data.lesson_id
    else:
        progress = CourseProgress(
            user_id=current_user.id,
            course_id=course_id,
            last_lesson_id=data.lesson_id,
        )
        db.add(progress)

    db.flush()
    db.refresh(progress)
    return progress.last_lesson_id
