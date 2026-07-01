"""课时管理路由。"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.response import success
from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.schemas.common import AuthUser, LessonCreate, LessonReorderItem, LessonUpdate
from app.services.lesson_service import (
    create_lesson,
    delete_lesson,
    format_lesson_out,
    get_lesson,
    get_lessons_by_course,
    reorder_lessons,
    update_lesson,
)

router = APIRouter(tags=["lessons"])


@router.get(
    "/courses/{course_id}/lessons",
    summary="获取课程课时列表",
    description="学生读取已发布课时；教师/管理员读取可管理范围内的全部课时。",
)
def list_lessons(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    lessons = get_lessons_by_course(db, course_id, current_user)
    return success([format_lesson_out(lesson) for lesson in lessons])


@router.post(
    "/courses/{course_id}/lessons",
    summary="创建课时",
    description="教师/管理员：为课程创建新课时。",
)
def add_lesson(
    course_id: int,
    data: LessonCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("teacher", "admin")),
):
    lesson = create_lesson(db, course_id, data, current_user)
    db.commit()
    db.refresh(lesson)
    return success(format_lesson_out(lesson))


@router.get(
    "/lessons/{lesson_id}",
    summary="获取课时详情",
    description="学生读取已发布课时；教师/管理员读取可管理范围内的课时。",
)
def get_lesson_detail(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    lesson = get_lesson(db, lesson_id, current_user)
    return success(format_lesson_out(lesson))


@router.put(
    "/lessons/{lesson_id}",
    summary="更新课时",
    description="教师/管理员：更新课时标题、内容、状态或排序。",
)
def edit_lesson(
    lesson_id: int,
    data: LessonUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("teacher", "admin")),
):
    lesson = update_lesson(db, lesson_id, data, current_user)
    db.commit()
    db.refresh(lesson)
    return success(format_lesson_out(lesson))


@router.delete(
    "/lessons/{lesson_id}",
    summary="删除课时",
    description="教师/管理员：删除指定课时。",
)
def remove_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("teacher", "admin")),
):
    if not delete_lesson(db, lesson_id, current_user):
        raise BusinessException(404, "课时不存在")
    db.commit()
    return success({"id": lesson_id})


@router.post(
    "/courses/{course_id}/lessons/reorder",
    summary="批量排序课时",
    description="教师/管理员：批量更新课程下课时的 sort_order。",
)
def reorder_course_lessons(
    course_id: int,
    items: List[LessonReorderItem],
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("teacher", "admin")),
):
    reorder_lessons(db, course_id, items, current_user)
    db.commit()
    return success()
