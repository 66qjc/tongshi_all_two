"""Material routes"""
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success, paginated_success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, MaterialCreate, MaterialUpdate
from app.services.material_service import (
    can_view_course_materials, list_materials, create_material,
    update_material, delete_material, resolve_material_file_for_user,
    format_material_preview,
)
from app.services.material_preview_service import generate_material_preview

router = APIRouter(tags=["materials"])


def _format_material(m):
    return {
        "id": m.id, "course_id": m.course_id,
        "course_name": m.course.name if m.course else "",
        "type": m.type, "title": m.title, "url": m.url,
        "duration": m.duration, "pages": m.pages,
        "size": m.size, "date": m.date,
        "file_id": m.file_id,
        "source_material_id": m.source_material_id,
        "is_synced": bool(m.source_material_id),
        "stage_id": m.stage_id,
        "preview": format_material_preview(m.preview),
    }


@router.get("/courses/{course_id}/contents", summary="获取课程内容", description="返回指定课程的所有视频和 PDF 学习资料，支持关键词搜索")
def get_course_contents(
    course_id: int,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    if not can_view_course_materials(db, course_id, current_user.id, current_user.role):
        raise BusinessException(404, "课程不存在")
    materials, _ = list_materials(db, course_id, keyword=keyword)
    return success([_format_material(m) for m in materials])


@router.get("/materials", summary="获取全部资料列表", description="教师端：按课程返回所有学习资料，支持分页和关键词搜索")
def get_all_materials(
    course_id: int | None = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    materials, total = list_materials(
        db,
        course_id,
        current_user.id,
        keyword,
        page,
        page_size,
        include_public_sources=False,
    )
    return paginated_success([_format_material(m) for m in materials], total, page, page_size)


@router.post("/materials", summary="新增资料", description="教师端：为指定课程添加视频或 PDF 学习资料")
def add_material(
    data: MaterialCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    m = create_material(db, data.course_id, data.type, data.title, data.url, data.size, data.file_id, data.stage_id, current_user.id)
    if not m:
        raise BusinessException(404, "课程不存在")
    return success({"id": m.id})


@router.put("/materials/{material_id}", summary="更新资料", description="教师端：修改资料标题或所属阶段")
def edit_material(
    material_id: int,
    data: MaterialUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    clear_stage = "stage_id" in data.model_fields_set and data.stage_id is None
    m = update_material(db, material_id, data.title, data.stage_id, current_user.id, clear_stage_id=clear_stage)
    if not m:
        raise BusinessException(404, "资料不存在")
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


@router.get("/materials/{material_id}/file", summary="预览资料文件", description="鉴权后通过 Nginx 内部跳转传输资料文件")
def open_material_file(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    material, stored, accel_path = resolve_material_file_for_user(db, material_id, current_user.id, current_user.role)
    if not material:
        raise BusinessException(404, "资料不存在")

    filename = stored.original_name or stored.stored_name or material.title or "material"
    encoded = quote(filename, encoding="utf-8")
    headers = {
        "X-Accel-Redirect": accel_path,
        "Content-Disposition": f"inline; filename*=UTF-8''{encoded}",
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=0",
    }
    if stored.size_bytes:
        headers["Content-Length"] = str(stored.size_bytes)
    return Response(content=b"", media_type=stored.content_type or "application/octet-stream", headers=headers)


@router.post("/materials/{material_id}/preview/rebuild", summary="重新生成资料预览")
def rebuild_material_preview(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    material, _, _ = resolve_material_file_for_user(db, material_id, current_user.id, current_user.role)
    if not material:
        raise BusinessException(404, "资料不存在")
    preview = generate_material_preview(db, material_id)
    return success({
        "status": preview.status,
        "cover_file_id": preview.cover_file_id,
        "summary": preview.summary,
        "page_count": preview.page_count,
        "duration_seconds": preview.duration_seconds,
        "resolution": preview.resolution,
        "error_message": preview.error_message,
    })
