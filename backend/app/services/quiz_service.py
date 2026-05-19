"""Quiz service"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
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

    # Update per-chapter progress
    sp = db.query(StudentProgress).filter(
        StudentProgress.user_id == user_id,
        StudentProgress.chapter_id == question.chapter_id,
    ).first()
    if not sp:
        sp = StudentProgress(user_id=user_id, chapter_id=question.chapter_id)
        db.add(sp)

    sp.questions_done += 1
    total = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.question_id.in_(
            db.query(Question.id).filter(Question.chapter_id == question.chapter_id)
        ),
    ).count()
    correct = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.is_correct == True,
        QuizAttempt.question_id.in_(
            db.query(Question.id).filter(Question.chapter_id == question.chapter_id)
        ),
    ).count()
    sp.accuracy = int(correct / total * 100) if total > 0 else 0

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
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
    ).order_by(QuizAttempt.answered_at.desc()).limit(limit).all()

    result = []
    for a in attempts:
        q = db.query(Question).filter(Question.id == a.question_id).first()
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
    questions_done = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).count()
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


def get_chapter_quiz_stats(db: Session, user_id: str, chapter_id: int):
    sp = db.query(StudentProgress).filter(
        StudentProgress.user_id == user_id,
        StudentProgress.chapter_id == chapter_id,
    ).first()
    return {
        "chapter_id": chapter_id,
        "questions_done": sp.questions_done if sp else 0,
        "accuracy": sp.accuracy if sp else 0,
    }
