"""悟页面图文内容管理路由（管理员增删改查，公开只读）"""
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.response import success
from app.core.security import get_current_user, require_role
from app.db.session import get_db
from app.models.entities import ShowcaseItem
from app.schemas.common import AuthUser, ShowcaseItemCreate, ShowcaseItemOut, ShowcaseItemUpdate
from app.services.file_service import build_file_url

router = APIRouter(prefix="/showcase", tags=["showcase"])


def _to_out(item: ShowcaseItem) -> ShowcaseItemOut:
    """将 ORM 对象转换为输出 Schema，补充 cover_url"""
    cover_url = ""
    if item.cover_file_id:
        cover_url = build_file_url(item.cover_file_id)
    return ShowcaseItemOut(
        id=item.id,
        section=item.section,
        title=item.title,
        content=item.content or "",
        cover_url=cover_url,
        link_url=item.link_url or "",
        sort_order=item.sort_order,
        is_active=item.is_active,
        created_at=item.created_at,
    )


@router.get("", summary="获取悟页面展示内容（公开）")
def list_showcase(db: Session = Depends(get_db)):
    """公开接口：返回所有激活内容，按 section 分组，每组按 sort_order 升序"""
    items = (
        db.query(ShowcaseItem)
        .filter(ShowcaseItem.is_active == True)
        .order_by(ShowcaseItem.section, ShowcaseItem.sort_order)
        .all()
    )
    # 按 section 分组返回
    grouped: Dict[str, List] = {}
    for item in items:
        grouped.setdefault(item.section, []).append(_to_out(item))
    return success(grouped)


@router.get("/admin", summary="管理员获取所有内容（含未激活）")
def list_showcase_admin(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("admin")),
):
    """管理员接口：返回所有内容（含 is_active=False），按 section + sort_order 排序"""
    items = (
        db.query(ShowcaseItem)
        .order_by(ShowcaseItem.section, ShowcaseItem.sort_order)
        .all()
    )
    grouped: Dict[str, List] = {}
    for item in items:
        grouped.setdefault(item.section, []).append(_to_out(item))
    return success(grouped)


@router.post("", summary="管理员新增图文内容")
def create_showcase_item(
    data: ShowcaseItemCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("admin")),
):
    """仅管理员可操作"""
    allowed_sections = {"welfare", "reading_club"}
    if data.section not in allowed_sections:
        raise BusinessException(
            400, f"section 只允许：{', '.join(allowed_sections)}")

    item = ShowcaseItem(
        section=data.section,
        title=data.title,
        content=data.content,
        cover_file_id=data.cover_file_id,
        link_url=data.link_url,
        sort_order=data.sort_order,
        created_by=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return success(_to_out(item))


@router.put("/{item_id}", summary="管理员修改图文内容")
def update_showcase_item(
    item_id: int,
    data: ShowcaseItemUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("admin")),
):
    """仅管理员可操作"""
    item = db.query(ShowcaseItem).filter(ShowcaseItem.id == item_id).first()
    if not item:
        raise BusinessException(404, "内容不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    item.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(item)
    return success(_to_out(item))


@router.delete("/{item_id}", summary="管理员删除图文内容")
def delete_showcase_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("admin")),
):
    """仅管理员可操作，物理删除"""
    item = db.query(ShowcaseItem).filter(ShowcaseItem.id == item_id).first()
    if not item:
        raise BusinessException(404, "内容不存在")

    db.delete(item)
    db.commit()
    return success({"id": item_id})
