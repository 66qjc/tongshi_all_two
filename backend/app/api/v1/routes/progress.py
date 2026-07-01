"""学习进度路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.core.security import require_roles
from app.db.session import get_db
from app.schemas.common import AuthUser, CourseProgressIn
from app.services.progress_service import get_progress, save_progress

router = APIRouter(tags=["progress"])


@router.get("/courses/{course_id}/progress", summary="获取学习进度", description="学生/教师/管理员：获取当前用户在指定课程的学习进度")
def read_progress(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("student", "teacher", "admin")),
):
    last_lesson_id = get_progress(db, course_id, current_user)
    return success({"last_lesson_id": last_lesson_id})


@router.post("/courses/{course_id}/progress", summary="保存学习进度", description="学生/教师/管理员：保存当前用户在指定课程的学习进度")
def write_progress(
    course_id: int,
    data: CourseProgressIn,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("student", "teacher", "admin")),
):
    last_lesson_id = save_progress(db, course_id, data, current_user)
    db.commit()
    return success({"last_lesson_id": last_lesson_id})
