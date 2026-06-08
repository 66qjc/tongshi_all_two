"""Quiz service"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.core.exceptions import BusinessException
from app.models.entities import Class, Question, QuizAttempt, StudentClassEnrollment
from app.core.timezone_utils import to_beijing_iso, beijing_today
from app.services.task_service import get_accessible_assignment, validate_assignment_available


def _student_can_access_course(db: Session, user_id: str, course_id: int) -> bool:
    """校验学生是否加入了题目所属课程。"""
    return db.query(StudentClassEnrollment).join(
        Class, Class.id == StudentClassEnrollment.class_id,
    ).filter(
        StudentClassEnrollment.user_id == user_id,
        Class.course_id == course_id,
    ).first() is not None


def submit_answer(db: Session, user_id: str, question_id: int, user_answer: str, role: str = "student", announcement_id: int | None = None):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise BusinessException(404, "题目不存在")
    if role == "student":
        if announcement_id is not None:
            ann = get_accessible_assignment(db, user_id, announcement_id)
            if not ann:
                raise BusinessException(404, "题目任务不存在")
            validate_assignment_available(ann)
            question_ids = ann.question_ids if isinstance(ann.question_ids, list) else []
            if question.course_id != ann.course_id or question.id not in question_ids:
                raise BusinessException(404, "题目不存在")
        elif not _student_can_access_course(db, user_id, question.course_id):
            raise BusinessException(404, "题目不存在")

    if question.type == "multi_choice":
        # 多选题：将用户答案和标准答案各自排序后比较
        user_sorted = "".join(sorted(user_answer.strip().upper()))
        correct_sorted = "".join(sorted(question.answer.strip().upper()))
        is_correct = user_sorted == correct_sorted
    else:
        is_correct = user_answer.strip().upper() == question.answer.strip().upper()
    attempt = QuizAttempt(
        user_id=user_id,
        question_id=question_id,
        announcement_id=announcement_id,
        user_answer=user_answer,
        is_correct=is_correct,
    )
    db.add(attempt)
    db.commit()
    return {
        "id": attempt.id,
        "question_id": question_id,
        "user_answer": user_answer,
        "is_correct": is_correct,
        "correct_answer": question.answer,
        "explanation": question.explanation,
        "answered_at": to_beijing_iso(attempt.answered_at),
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
            "answered_at": to_beijing_iso(a.answered_at),
            "stem": q.stem if q else "",
        })
    return result


def get_quiz_stats(db: Session, user_id: str):
    # 先取学生所属课程范围，四个指标统一限定在此范围
    student_course_ids = (
        db.query(Question.course_id)
        .join(Class, Class.course_id == Question.course_id)
        .join(StudentClassEnrollment, StudentClassEnrollment.class_id == Class.id)
        .filter(StudentClassEnrollment.user_id == user_id)
        .distinct()
        .all()
    )
    student_course_id_list = [row.course_id for row in student_course_ids]
    if not student_course_id_list:
        return {
            "total_questions": 0,
            "questions_done": 0,
            "accuracy": 0,
            "today_count": 0,
        }

    course_question_ids = db.query(Question.id).filter(Question.course_id.in_(student_course_id_list))

    total_questions = db.query(Question).filter(
        Question.course_id.in_(student_course_id_list)
    ).count()
    questions_done = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.question_id.in_(course_question_ids),
    ).count()
    correct = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.is_correct == True,
        QuizAttempt.question_id.in_(course_question_ids),
    ).count()
    accuracy = int(correct / questions_done * 100) if questions_done > 0 else 0

    today = beijing_today()
    today_count = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.question_id.in_(course_question_ids),
        QuizAttempt.answered_at >= today,
    ).count()

    return {
        "total_questions": total_questions,
        "questions_done": questions_done,
        "accuracy": accuracy,
        "today_count": today_count,
    }


def get_course_quiz_stats(db: Session, user_id: str, course_id: int):
    # 权限校验：学生必须加入该课程才能查看统计
    if not _student_can_access_course(db, user_id, course_id):
        raise BusinessException(404, "课程不存在或无权限访问")

    # 计算该用户在该课程下的答题统计
    course_question_ids = db.query(Question.id).filter(Question.course_id == course_id)

    questions_done = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.question_id.in_(course_question_ids),
    ).count()

    correct_count = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.is_correct == True,
        QuizAttempt.question_id.in_(course_question_ids),
    ).count()

    accuracy = int(correct_count / questions_done * 100) if questions_done > 0 else 0

    return {
        "course_id": course_id,
        "questions_done": questions_done,
        "accuracy": accuracy,
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
            "answered_at": to_beijing_iso(a.answered_at),
        })
    return result
