"""Quiz routes"""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_role, require_roles
from app.core.response import success
from app.schemas.common import AuthUser, QuizSubmitRequest
from app.services.quiz_service import (
    submit_answer,
    get_quiz_history,
    get_quiz_stats,
    get_course_quiz_stats,
    list_visible_practice_questions,
)

router = APIRouter(prefix="/quiz", tags=["quiz"])


def _format_practice_question(q) -> dict:
    """学生练习题池：不返回答案与解析字段，防止前端泄露。"""
    return {
        "id": q.id,
        "type": q.type,
        "course_id": q.course_id,
        "course_name": (getattr(q, "mount_course_name_snapshot", None) or ""),
        "stem": q.stem,
        "options": q.options or [],
        "tags": q.tags or [],
        "star_rating": q.star_rating if q.star_rating is not None else 3,
    }


@router.post("/submit", summary="提交答案", description="学生端：提交单道题目的答案，返回批改结果（正确/错误 + 解析）")
def submit(
    data: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    result = submit_answer(db, current_user.id, data.question_id, data.user_answer, current_user.role, data.announcement_id)
    return success(result)


@router.get("/questions", summary="全局练习题池", description="学生端：返回当前可见的全站自由练习题，隐藏答案与解析")
def practice_questions(
    ids: str | None = Query(default=None, description="逗号分隔题目 ID"),
    random: int | None = Query(default=None, ge=1, le=200, description="随机抽取数量"),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    id_list = None
    if ids:
        id_list = [int(part) for part in ids.split(",") if part.strip().isdigit()]
    questions = list_visible_practice_questions(
        db,
        current_user.id,
        ids=id_list,
        random_count=random,
    )
    return success([_format_practice_question(q) for q in questions])


@router.get("/history", summary="答题历史", description="学生端：获取最近 N 次答题记录（含题目和答案）")
def history(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    return success(get_quiz_history(db, current_user.id, limit))


@router.get("/stats", summary="答题统计总览", description="返回总题目数、已完成数、正确率、今日答题数")
def stats(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("student", "teacher", "admin")),
):
    return success(get_quiz_stats(db, current_user.id))


@router.get(
    "/stats/{course_id}",
    summary="课程答题统计（已弃用）",
    description="兼容旧客户端：委托全局统计，并返回弃用响应头",
)
def course_stats(
    course_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    _ = course_id
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/quiz/stats>; rel="successor-version"'
    # 兼容：仍返回全局统计口径，避免课程卡片重复假统计
    data = get_quiz_stats(db, current_user.id)
    return success({
        "course_id": course_id,
        "questions_done": data.get("questions_done", 0),
        "accuracy": data.get("accuracy", 0),
        "total_questions": data.get("total_questions", 0),
    })
