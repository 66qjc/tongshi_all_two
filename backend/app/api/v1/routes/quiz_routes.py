"""Quiz routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.schemas.common import AuthUser, QuizSubmitRequest
from app.services.quiz_service import submit_answer, get_quiz_history, get_quiz_stats, get_course_quiz_stats

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/submit", summary="提交答案", description="学生端：提交单道题目的答案，返回批改结果（正确/错误 + 解析）")
def submit(
    data: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    result = submit_answer(db, current_user.id, data.question_id, data.user_answer)
    return success(result)


@router.get("/history", summary="答题历史", description="学生端：获取最近 N 次答题记录（含题目和答案）")
def history(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success(get_quiz_history(db, current_user.id, limit))


@router.get("/stats", summary="答题统计总览", description="学生端：返回总题目数、已完成数、正确率、今日答题数")
def stats(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success(get_quiz_stats(db, current_user.id))


@router.get("/stats/{course_id}", summary="课程答题统计", description="学生端：返回指定课程的答题完成数和正确率")
def course_stats(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success(get_course_quiz_stats(db, current_user.id, course_id))
