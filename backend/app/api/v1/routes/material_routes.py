"""Material routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, MaterialCreate
from app.services.material_service import list_materials, list_all_materials, create_material, delete_material

router = APIRouter(tags=["materials"])


def _format_material(m):
    return {
        "id": m.id, "chapter_id": m.chapter_id,
        "chapter": m.chapter.title if m.chapter else "",
        "type": m.type, "title": m.title, "url": m.url,
        "duration": m.duration, "pages": m.pages,
        "size": m.size, "date": m.date,
    }


@router.get("/chapters/{chapter_id}/contents")
def get_chapter_contents(
    chapter_id: int,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    materials = list_materials(db, chapter_id)
    return success([_format_material(m) for m in materials])


@router.get("/materials")
def get_all_materials(
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    materials = list_all_materials(db)
    return success([_format_material(m) for m in materials])


@router.post("/materials")
def add_material(
    data: MaterialCreate,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    m = create_material(db, data.chapter_id, data.type, data.title)
    if not m:
        raise BusinessException(404, "章节不存在")
    return success({"id": m.id})


@router.delete("/materials/{material_id}")
def remove_material(
    material_id: int,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    if not delete_material(db, material_id):
        raise BusinessException(404, "资料不存在")
    return success()
