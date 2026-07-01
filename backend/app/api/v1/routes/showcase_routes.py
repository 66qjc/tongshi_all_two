"""悟页面图文内容管理路由（管理员增删改查，公开只读）"""
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.response import success
from app.core.security import get_current_user, require_role
from app.db.session import get_db
from app.models.entities import ShowcaseItem, ShowcaseItemImage
from app.schemas.common import AuthUser, ShowcaseItemCreate, ShowcaseItemOut, ShowcaseItemUpdate, ShowcaseItemImageOut
from app.models.entities import StoredFile
from app.services.file_service import build_file_url


# 允许的内容块类型
_ALLOWED_BLOCK_TYPES = {"text", "image"}


def _validate_content_blocks(blocks, db: Session) -> list:
    """校验图文内容块结构，返回清洗后的块列表。

    text 块：data.text 必须为非空字符串；
    image 块：data.file_id 必须为正整数且对应 stored_files 存在，caption 可选字符串。
    """
    if not isinstance(blocks, list):
        raise BusinessException(400, "内容块必须为数组")

    cleaned = []
    for block in blocks:
        if not isinstance(block, dict) or "type" not in block or "data" not in block:
            raise BusinessException(400, "内容块格式错误：缺少 type 或 data")
        btype = block["type"]
        data = block["data"]
        if not isinstance(data, dict):
            raise BusinessException(400, "内容块 data 必须为对象")
        if btype not in _ALLOWED_BLOCK_TYPES:
            raise BusinessException(400, f"不支持的内容块类型：{btype}")

        if btype == "text":
            text = (data.get("text") or "").strip()
            if not text:
                raise BusinessException(400, "文字段落内容不能为空")
            cleaned.append({"type": "text", "data": {"text": text}})
        else:  # image
            file_id = data.get("file_id")
            if not isinstance(file_id, int) or file_id <= 0:
                raise BusinessException(400, "图片块缺少有效的 file_id")
            exists = db.query(StoredFile.id).filter(StoredFile.id == file_id).first()
            if not exists:
                raise BusinessException(400, f"图片块引用的文件不存在：file_id={file_id}")
            caption = (data.get("caption") or "").strip()
            entry = {"type": "image", "data": {"file_id": file_id}}
            if caption:
                entry["data"]["caption"] = caption
            cleaned.append(entry)

    return cleaned


def _derive_summary(blocks) -> str:
    """从内容块拼接纯文本摘要，截断到约 120 字，用于列表预览。"""
    parts = []
    for b in blocks or []:
        if b.get("type") == "text" and b.get("data", {}).get("text"):
            parts.append(b["data"]["text"])
    summary = " ".join(parts).strip()
    if len(summary) > 120:
        summary = summary[:120] + "…"
    return summary
router = APIRouter(prefix="/showcase", tags=["showcase"])


def _to_out(item: ShowcaseItem) -> ShowcaseItemOut:
    """将 ORM 对象转换为输出 Schema，补充 cover_url 和 images"""
    cover_url = ""
    if item.cover_file_id:
        cover_url = build_file_url(item.cover_file_id)

    images = []
    for img in item.images:
        images.append(ShowcaseItemImageOut(
            id=img.id,
            file_id=img.file_id,
            url=build_file_url(img.file_id),
            sort_order=img.sort_order,
        ))

    return ShowcaseItemOut(
        id=item.id,
        section=item.section,
        title=item.title,
        content=item.content or "",
        content_blocks=item.content_blocks or [],
        cover_url=cover_url,
        images=images,
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

    content_blocks = _validate_content_blocks(data.content_blocks, db) if data.content_blocks else None
    # 有内容块时由块文本生成摘要；否则沿用传入的 content
    summary = _derive_summary(content_blocks) if content_blocks else (data.content or "")

    item = ShowcaseItem(
        section=data.section,
        title=data.title,
        content=summary,
        content_blocks=content_blocks,
        cover_file_id=data.cover_file_id,
        link_url=data.link_url,
        sort_order=data.sort_order,
        created_by=current_user.id,
    )
    db.add(item)
    db.flush()

    # 创建多图片记录
    for idx, file_id in enumerate(data.image_file_ids):
        image = ShowcaseItemImage(
            showcase_item_id=item.id,
            file_id=file_id,
            sort_order=idx,
        )
        db.add(image)

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
    # 单独处理 image_file_ids，因为它需要特殊逻辑
    image_file_ids = update_data.pop("image_file_ids", None)
    # 单独处理 content_blocks，需要校验并同步摘要
    content_blocks_raw = update_data.pop("content_blocks", None)

    for field, value in update_data.items():
        setattr(item, field, value)

    if content_blocks_raw is not None:
        cleaned = _validate_content_blocks(content_blocks_raw, db)
        item.content_blocks = cleaned
        # 有块时用块文本覆盖摘要；清空块时保留原 content
        new_summary = _derive_summary(cleaned)
        if new_summary:
            item.content = new_summary
    item.updated_at = datetime.now(timezone.utc)

    # 如果提供了 image_file_ids，则更新多图片
    if image_file_ids is not None:
        # 删除旧的图片记录
        db.query(ShowcaseItemImage).filter(
            ShowcaseItemImage.showcase_item_id == item_id
        ).delete()
        # 创建新的图片记录
        for idx, file_id in enumerate(image_file_ids):
            image = ShowcaseItemImage(
                showcase_item_id=item_id,
                file_id=file_id,
                sort_order=idx,
            )
            db.add(image)

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


@router.delete("/{item_id}/images/{image_id}", summary="管理员删除单张图片")
def delete_showcase_image(
    item_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("admin")),
):
    """仅管理员可操作，删除图文内容中的单张图片"""
    image = db.query(ShowcaseItemImage).filter(
        ShowcaseItemImage.id == image_id,
        ShowcaseItemImage.showcase_item_id == item_id,
    ).first()
    if not image:
        raise BusinessException(404, "图片不存在")

    db.delete(image)
    db.commit()
    return success({"id": image_id})
