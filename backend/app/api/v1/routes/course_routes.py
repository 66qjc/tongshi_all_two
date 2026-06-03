"""Course routes — independent /courses endpoints.

Design doc 01 requires courses to have their own top-level route
instead of being nested under /questions/courses.

The old /questions/courses endpoints are kept in question_routes.py
for backward compatibility; both call the same service functions.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, CourseCreateRequest, CourseUpdateRequest
from app.services.question_service import (
    create_course,
    update_course,
    delete_course,
    get_course_detail,
    add_public_course,
)
from app.services.course_response_service import build_course_detail, build_course_list

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", summary="课程列表", description="获取所有课程（学生按班级关联，教师按归属）")
def get_courses(db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = build_course_list(db, current_user)
    if current_user.role == "student" and isinstance(data, dict) and data.get("hint") is None:
        return success(data["courses"])
    return success(data)


@router.post("", summary="创建课程", description="教师端：创建新课程")
def add_course(data: CourseCreateRequest, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    course = create_course(db, data.name.strip(), current_user.id)
    return success({"id": course.id})


@router.post("/{course_id}/add", summary="添加公共课程", description="教师端：将公共课程添加为自己的课程")
def add_public_course_to_teacher(course_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    course = add_public_course(db, course_id, current_user.id)
    return success({"id": course.id})


@router.get("/{course_id}", summary="课程详情", description="返回课程信息和资料、题目、班级统计")
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    teacher_id = current_user.id if current_user.role == "teacher" else None
    detail = get_course_detail(db, course_id, teacher_id)
    if not detail:
        raise BusinessException(404, "课程不存在")
    return success(build_course_detail(db, detail, current_user))


@router.put("/{course_id}", summary="修改课程名称", description="教师端：修改指定课程的名称")
def edit_course(course_id: int, data: CourseUpdateRequest, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    course = update_course(db, course_id, data.name.strip(), current_user.id)
    if not course:
        raise BusinessException(404, "课程不存在")
    return success()


@router.delete("/{course_id}", summary="删除课程", description="教师端：删除指定课程")
def remove_course(course_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    if not delete_course(db, course_id, current_user.id):
        raise BusinessException(404, "课程不存在")
    return success()
