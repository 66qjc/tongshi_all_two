"""Chapter routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, ChapterUpdate
from app.services.chapter_service import list_chapters, get_chapter, update_chapter

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.get("")
def get_chapters(db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    return success(list_chapters(db, current_user.id))


@router.get("/{num}")
def get_chapter_detail(num: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    ch = get_chapter(db, num)
    if not ch:
        raise BusinessException(404, "章节不存在")
    return success({
        "id": ch.id, "num": ch.num, "title": ch.title,
        "desc": ch.desc, "topics": ch.topics, "status": ch.status,
    })


@router.patch("/{chapter_id}")
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
