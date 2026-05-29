"""Material routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, MaterialCreate
from app.services.material_service import list_materials, create_material, delete_material

router = APIRouter(tags=["materials"])


def _format_material(m):
    return {
        "id": m.id, "course_id": m.course_id,
        "course_name": m.course.name if m.course else "",
        "type": m.type, "title": m.title, "url": m.url,
        "duration": m.duration, "pages": m.pages,
        "size": m.size, "date": m.date,
        "file_id": m.file_id,
    }


@router.get("/courses/{course_id}/contents", summary="获取课程内容", description="返回指定课程的所有视频和 PDF 学习资料")
def get_course_contents(
    course_id: int,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    materials = list_materials(db, course_id)
    return success([_format_material(m) for m in materials])


@router.get("/materials", summary="获取全部资料列表", description="教师端：按课程返回所有学习资料")
def get_all_materials(
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    materials = list_materials(db, course_id, current_user.id)
    return success([_format_material(m) for m in materials])


@router.post("/materials", summary="新增资料", description="教师端：为指定课程添加视频或 PDF 学习资料")
def add_material(
    data: MaterialCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    m = create_material(db, data.course_id, data.type, data.title, data.url, data.size, data.file_id, current_user.id)
    if not m:
        raise BusinessException(404, "课程不存在")
    return success({"id": m.id})


@router.delete("/materials/{material_id}", summary="删除资料", description="教师端：删除指定的学习资料")
def remove_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    if not delete_material(db, material_id, current_user.id):
        raise BusinessException(404, "资料不存在")
    return success()
