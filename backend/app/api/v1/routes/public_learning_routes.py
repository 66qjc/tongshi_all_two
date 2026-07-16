"""公开学习馆路由。"""
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.response import success
from app.db.session import get_db
from app.services.public_learning_service import (
    build_public_course_detail,
    list_public_courses,
    list_public_lessons,
    list_public_materials,
    resolve_public_material_file,
)

router = APIRouter(prefix="/public/learning", tags=["public-learning"])


@router.get("/courses", summary="公开课程列表", description="游客读取公开课程列表。")
def get_public_courses(keyword: Optional[str] = None, db: Session = Depends(get_db)):
    return success(list_public_courses(db, keyword))


@router.get("/courses/{course_id}", summary="公开课程详情", description="游客读取公开课程详情和资料。")
def get_public_course(course_id: int, db: Session = Depends(get_db)):
    return success(build_public_course_detail(db, course_id))


@router.get("/courses/{course_id}/lessons", summary="公开课时列表", description="游客读取公开课程下已发布课时。")
def get_public_course_lessons(course_id: int, db: Session = Depends(get_db)):
    return success(list_public_lessons(db, course_id))


@router.get("/materials", summary="公开资料列表", description="游客读取公开课程资料。")
def get_public_materials(
    course_id: Optional[int] = None,
    keyword: Optional[str] = None,
    limit: int = 12,
    db: Session = Depends(get_db),
):
    return success(list_public_materials(db, course_id=course_id, keyword=keyword, limit=limit))


@router.get("/materials/{material_id}/file", summary="公开资料预览", description="游客预览公开课程下的资料文件。")
def open_public_material_file(material_id: int, db: Session = Depends(get_db)):
    _, stored, headers = resolve_public_material_file(db, material_id)
    response = Response(
        content=b"",
        media_type=stored.content_type or "application/octet-stream",
        headers=headers,
    )
    if "content-length" in response.headers:
        del response.headers["content-length"]
    return response
