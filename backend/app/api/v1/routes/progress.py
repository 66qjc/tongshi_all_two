"""学习进度路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.core.security import require_role, require_roles
from app.db.session import get_db
from app.schemas.common import AuthUser, CourseProgressIn, LessonProgressIn
from app.services.progress_service import (
    get_class_student_progress,
    get_course_analytics,
    get_course_progress_summary,
    report_lesson_progress,
    save_progress,
)

router = APIRouter(tags=["progress"])


@router.get("/courses/{course_id}/progress", summary="获取学习进度", description="学生/教师/管理员：获取当前用户在指定课程的课时级学习进度")
def read_progress(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("student", "teacher", "admin")),
):
    return success(get_course_progress_summary(db, course_id, current_user))


@router.post("/courses/{course_id}/progress", summary="保存学习进度", description="学生/教师/管理员：保存当前用户在指定课程的最后阅读课时")
def write_progress(
    course_id: int,
    data: CourseProgressIn,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("student", "teacher", "admin")),
):
    last_lesson_id = save_progress(db, course_id, data, current_user)
    db.commit()
    return success({"last_lesson_id": last_lesson_id})


@router.post(
    "/courses/{course_id}/lessons/{lesson_id}/progress",
    summary="上报课时学习进度",
    description="学生/教师/管理员：上报课时完成百分比、播放位置和本次学习时长。",
)
def write_lesson_progress(
    course_id: int,
    lesson_id: int,
    data: LessonProgressIn,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("student", "teacher", "admin")),
):
    result = report_lesson_progress(db, course_id, lesson_id, data, current_user)
    db.commit()
    return success(result)


@router.get(
    "/classes/{class_id}/students/{student_id}/progress",
    summary="查看班级学生进度",
    description="教师端：查看自己班级内指定学生的课程课时进度。",
)
def read_class_student_progress(
    class_id: int,
    student_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    return success(get_class_student_progress(db, class_id, student_id, current_user))


@router.get(
    "/courses/{course_id}/analytics",
    summary="课程学习统计",
    description="教师/管理员：查看课程整体完成率、平均学习时长和低完成课时。",
)
def read_course_analytics(
    course_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("teacher", "admin")),
):
    return success(get_course_analytics(db, course_id, current_user, page, page_size))
