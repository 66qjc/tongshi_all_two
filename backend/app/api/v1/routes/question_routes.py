"""Question routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, QuestionCreate, QuestionUpdate
from app.services.question_service import (
    list_questions, create_question, update_question, delete_question,
    get_chapter_questions,
)

router = APIRouter(prefix="/questions", tags=["questions"])


def _format_question(q):
    return {
        "id": q.id, "type": q.type, "chapter_id": q.chapter_id,
        "stem": q.stem, "options": q.options,
        "answer": q.answer, "explanation": q.explanation,
    }


@router.get("")
def get_questions(
    chapter_id: int = None,
    type: str = None,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    questions = list_questions(db, chapter_id, type)
    return success([_format_question(q) for q in questions])


@router.get("/chapter/{chapter_id}")
def get_chapter_questions_for_quiz(
    chapter_id: int,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    questions = get_chapter_questions(db, chapter_id)
    return success([_format_question(q) for q in questions])


@router.post("")
def add_question(
    data: QuestionCreate,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    q = create_question(db, data.model_dump())
    return success({"id": q.id})


@router.put("/{question_id}")
def edit_question(
    question_id: int,
    data: QuestionUpdate,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    q = update_question(db, question_id, data.model_dump(exclude_unset=True))
    if not q:
        raise BusinessException(404, "题目不存在")
    return success()


@router.delete("/{question_id}")
def remove_question(
    question_id: int,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    if not delete_question(db, question_id):
        raise BusinessException(404, "题目不存在")
    return success()
