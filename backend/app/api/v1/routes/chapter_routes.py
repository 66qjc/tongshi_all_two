"""Chapter routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, ChapterCreate, ChapterManageUpdate, ChapterUpdate, ChapterScheduleUpdate
from app.services.chapter_service import list_chapters, get_chapter, create_chapter, update_chapter, delete_chapter

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.get("", summary="获取章节列表", description="返回所有章节及其学习进度、内容统计、排课时间")
def get_chapters(db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    return success(list_chapters(db, current_user.id))


@router.get("/{num}", summary="获取章节详情", description="根据章节编号（如 01）获取章节详细信息")
def get_chapter_detail(num: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    ch = get_chapter(db, num)
    if not ch:
        raise BusinessException(404, "章节不存在")
    return success({
        "id": ch.id, "num": ch.num, "title": ch.title,
        "desc": ch.desc, "topics": ch.topics, "status": ch.status,
        "course_id": ch.course_id,
        "day_of_week": ch.day_of_week or "",
        "class_periods": ch.class_periods or "",
        "schedule_note": ch.schedule_note or "",
    })


@router.post("", summary="新增章节", description="教师端：创建课程章节")
def add_chapter(
    data: ChapterCreate,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    ch = create_chapter(db, data.model_dump())
    return success({"id": ch.id})


@router.patch("/{chapter_id}", summary="更新章节状态", description="教师端：修改章节发布状态")
def update_chapter_status(
    chapter_id: int,
    data: ChapterUpdate,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    ch = update_chapter(db, chapter_id, data.model_dump(exclude_unset=True))
    if not ch:
        raise BusinessException(404, "章节不存在")
    return success()


@router.put("/{chapter_id}", summary="编辑章节", description="教师端：修改章节基础信息和排课信息")
def edit_chapter(
    chapter_id: int,
    data: ChapterManageUpdate,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    ch = update_chapter(db, chapter_id, data.model_dump())
    if not ch:
        raise BusinessException(404, "章节不存在")
    return success()


@router.put("/{chapter_id}/schedule", summary="更新章节排课时间", description="教师端：设置章节的上课星期、节次和备注")
def update_chapter_schedule(
    chapter_id: int,
    data: ChapterScheduleUpdate,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    ch = update_chapter(db, chapter_id, data.model_dump(exclude_unset=True))
    if not ch:
        raise BusinessException(404, "章节不存在")
    return success()


@router.delete("/{chapter_id}", summary="删除章节", description="教师端：删除无关联数据的章节")
def remove_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    if not delete_chapter(db, chapter_id):
        raise BusinessException(404, "章节不存在")
    return success()
