"""Quiz routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.schemas.common import AuthUser, QuizSubmitRequest
from app.services.quiz_service import submit_answer, get_quiz_history, get_quiz_stats, get_chapter_quiz_stats

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/submit")
def submit(
    data: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    result = submit_answer(db, current_user.id, data.question_id, data.user_answer)
    return success(result)


@router.get("/history")
def history(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success(get_quiz_history(db, current_user.id, limit))


@router.get("/stats")
def stats(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success(get_quiz_stats(db, current_user.id))


@router.get("/stats/{chapter_id}")
def chapter_stats(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success(get_chapter_quiz_stats(db, current_user.id, chapter_id))
