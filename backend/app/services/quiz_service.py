"""Quiz service"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.models.entities import Question, QuizAttempt, StudentProgress


def submit_answer(db: Session, user_id: str, question_id: int, user_answer: str):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return None

    is_correct = user_answer.strip().upper() == question.answer.strip().upper()
    attempt = QuizAttempt(
        user_id=user_id,
        question_id=question_id,
        user_answer=user_answer,
        is_correct=is_correct,
    )
    db.add(attempt)

    # 更新课程维度进度
    sp = db.query(StudentProgress).filter(
        StudentProgress.user_id == user_id,
        StudentProgress.course_id == question.course_id,
    ).first()
    if not sp:
        sp = StudentProgress(user_id=user_id, course_id=question.course_id)
        db.add(sp)

    # 先 flush 确保新增的 attempt 对后续查询可见（session 设置了 autoflush=False）
    db.flush()

    total = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.question_id.in_(
            db.query(Question.id).filter(
                Question.course_id == question.course_id)
        ),
    ).count()
    correct_count = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.is_correct == True,
        QuizAttempt.question_id.in_(
            db.query(Question.id).filter(
                Question.course_id == question.course_id)
        ),
    ).count()
    sp.questions_done = total
    sp.accuracy = int(correct_count / total * 100) if total > 0 else 0

    db.commit()
    return {
        "id": attempt.id,
        "question_id": question_id,
        "user_answer": user_answer,
        "is_correct": is_correct,
        "correct_answer": question.answer,
        "explanation": question.explanation,
        "answered_at": attempt.answered_at.isoformat() if attempt.answered_at else "",
    }


def get_quiz_history(db: Session, user_id: str, limit: int = 10):
    attempts = db.query(QuizAttempt).options(joinedload(QuizAttempt.question)).filter(
        QuizAttempt.user_id == user_id,
    ).order_by(QuizAttempt.answered_at.desc()).limit(limit).all()

    result = []
    for a in attempts:
        # 利用 ORM relationship 直接访问 Question，避免 N+1 查询
        q = a.question
        result.append({
            "id": a.id,
            "question_id": a.question_id,
            "user_answer": a.user_answer,
            "is_correct": a.is_correct,
            "correct_answer": q.answer if q else "",
            "explanation": q.explanation if q else "",
            "answered_at": a.answered_at.isoformat() if a.answered_at else "",
            "stem": q.stem if q else "",
        })
    return result


def get_quiz_stats(db: Session, user_id: str):
    total_questions = db.query(Question).count()
    questions_done = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id).count()
    correct = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id, QuizAttempt.is_correct == True,
    ).count()
    accuracy = int(correct / questions_done * 100) if questions_done > 0 else 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
    ).filter(
        QuizAttempt.answered_at >= today,
    ).count()

    return {
        "total_questions": total_questions,
        "questions_done": questions_done,
        "accuracy": accuracy,
        "today_count": today_count,
    }


def get_course_quiz_stats(db: Session, user_id: str, course_id: int):
    sp = db.query(StudentProgress).filter(
        StudentProgress.user_id == user_id,
        StudentProgress.course_id == course_id,
    ).first()
    return {
        "course_id": course_id,
        "questions_done": sp.questions_done if sp else 0,
        "accuracy": sp.accuracy if sp else 0,
    }


def get_wrong_questions(db: Session, user_id: str):
    """错题本：每道题取最近一次答题记录，仅保留仍答错的题"""
    from sqlalchemy import func as sa_func

    # 子查询：每道题的最新答题记录 id
    latest_sub = (
        db.query(sa_func.max(QuizAttempt.id).label("max_id"))
        .filter(QuizAttempt.user_id == user_id)
        .group_by(QuizAttempt.question_id)
        .subquery()
    )

    attempts = (
        db.query(QuizAttempt)
        .join(latest_sub, QuizAttempt.id == latest_sub.c.max_id)
        .filter(QuizAttempt.is_correct == False)  # noqa: E712
        .options(joinedload(QuizAttempt.question))
        .all()
    )

    result = []
    for a in attempts:
        q = a.question
        if not q:
            continue
        result.append({
            "question_id": q.id,
            "course_id": q.course_id,
            "stem": q.stem,
            "options": q.options,
            "answer": q.answer,
            "explanation": q.explanation,
            "user_answer": a.user_answer,
            "answered_at": a.answered_at.isoformat() if a.answered_at else "",
        })
    return result
