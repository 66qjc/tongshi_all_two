"""练习与错题本服务。"""
from datetime import datetime, timezone

from sqlalchemy import func as sa_func, case
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BusinessException
from app.core.timezone_utils import beijing_today, to_beijing_iso
from app.models.entities import Announcement, Class, Course, Question, QuizAttempt, StudentClassEnrollment, TaskCompletion
from app.services.access_control_service import student_can_access_course
from app.services.task_service import get_accessible_assignment, validate_assignment_available



def submit_answer(
    db: Session,
    user_id: str,
    question_id: int,
    user_answer: str,
    role: str = "student",
    announcement_id: int | None = None,
):
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
            if question.id not in question_ids:
                raise BusinessException(404, "题目不存在")
        elif not _student_has_any_course(db, user_id):
            raise BusinessException(404, "题目不存在")

    if question.type == "multi_choice":
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
    try:
        db.flush()
        if announcement_id is not None:
            _update_assignment_score(db, user_id, announcement_id)
        db.commit()
        db.refresh(attempt)
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "提交答案失败，请稍后重试")

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


def _student_has_any_course(db: Session, user_id: str) -> bool:
    """判断学生是否至少加入了一个有关联课程的班级。"""
    return db.query(StudentClassEnrollment).join(
        Class, Class.id == StudentClassEnrollment.class_id,
    ).filter(
        StudentClassEnrollment.user_id == user_id,
        Class.course_id.isnot(None),
    ).first() is not None


def get_quiz_stats(db: Session, user_id: str):
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

    course_question_ids = db.query(Question.id).filter(
        Question.course_id.in_(student_course_id_list)
    )

    total_questions = db.query(Question).filter(
        Question.course_id.in_(student_course_id_list)
    ).count()

    # 三次 COUNT 合并为一次聚合查询，减少数据库往返
    today = beijing_today()
    row = db.query(
        sa_func.count(QuizAttempt.id).label("done"),
        sa_func.sum(
            case((QuizAttempt.is_correct == True, 1), else_=0)  # noqa: E712
        ).label("correct"),
        sa_func.sum(
            case((QuizAttempt.answered_at >= today, 1), else_=0)
        ).label("today"),
    ).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.question_id.in_(course_question_ids),
    ).one()

    questions_done = row.done or 0
    correct = row.correct or 0
    today_count = row.today or 0
    accuracy = int(correct / questions_done * 100) if questions_done > 0 else 0

    return {
        "total_questions": total_questions,
        "questions_done": questions_done,
        "accuracy": accuracy,
        "today_count": today_count,
    }


def get_course_quiz_stats(db: Session, user_id: str, course_id: int):
    if not student_can_access_course(db, user_id, course_id):
        raise BusinessException(404, "课程不存在或无权限访问")

    # 设计说明：平台采用"全站共享题库"模式，任意题目均可在任意课程入口练习。
    # 因此自由练习统计不按 course_id 过滤题目归属，而是统计该学生全部自由练习记录
    # （announcement_id IS NULL）。课程入口仅用于权限验证，不限缩题目范围。
    row = db.query(
        sa_func.count(QuizAttempt.id).label("done"),
        sa_func.sum(
            case((QuizAttempt.is_correct == True, 1), else_=0)  # noqa: E712
        ).label("correct"),
    ).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.announcement_id.is_(None),
    ).one()

    questions_done = row.done or 0
    correct_count = row.correct or 0
    accuracy = int(correct_count / questions_done * 100) if questions_done > 0 else 0

    return {
        "course_id": course_id,
        "questions_done": questions_done,
        "accuracy": accuracy,
    }


def get_wrong_questions(db: Session, user_id: str):
    """每道题取最近一次答题记录，仅保留仍答错且属于当前已加入课程的题。"""
    from sqlalchemy import func as sa_func

    student_course_ids = [
        row.course_id
        for row in (
            db.query(Class.course_id)
            .join(StudentClassEnrollment, StudentClassEnrollment.class_id == Class.id)
            .filter(StudentClassEnrollment.user_id == user_id)
            .distinct()
            .all()
        )
    ]
    if not student_course_ids:
        return []

    latest_sub = (
        db.query(sa_func.max(QuizAttempt.id).label("max_id"))
        .filter(QuizAttempt.user_id == user_id)
        .group_by(QuizAttempt.question_id)
        .subquery()
    )

    attempts = (
        db.query(QuizAttempt)
        .join(latest_sub, QuizAttempt.id == latest_sub.c.max_id)
        .join(Question, Question.id == QuizAttempt.question_id)
        .filter(QuizAttempt.is_correct == False)  # noqa: E712
        .filter(Question.course_id.in_(student_course_ids))
        .options(joinedload(QuizAttempt.question))
        .all()
    )

    courses = db.query(Course).filter(Course.id.in_(student_course_ids)).all()
    course_names = {course.id: course.name for course in courses}
    result = []
    for a in attempts:
        q = a.question
        if not q:
            continue
        result.append({
            "question_id": q.id,
            "course_id": q.course_id,
            "course_name": course_names.get(q.course_id, ""),
            "type": q.type,
            "stem": q.stem,
            "options": q.options,
            "answer": q.answer,
            "explanation": q.explanation,
            "user_answer": a.user_answer,
            "answered_at": to_beijing_iso(a.answered_at),
        })
    return result


def _update_assignment_score(db: Session, user_id: str, announcement_id: int) -> None:
    """作业答题后自动计算并更新作业完成记录的分数。"""
    # 获取作业配置
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        return

    question_ids = announcement.question_ids if isinstance(announcement.question_ids, list) else []
    if not question_ids:
        return

    # 获取学生最新答题记录
    latest_attempt_ids = (
        db.query(sa_func.max(QuizAttempt.id).label("attempt_id"))
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.announcement_id == announcement_id,
            QuizAttempt.question_id.in_(question_ids)
        )
        .group_by(QuizAttempt.question_id)
        .subquery()
    )

    attempts = (
        db.query(QuizAttempt)
        .join(latest_attempt_ids, QuizAttempt.id == latest_attempt_ids.c.attempt_id)
        .all()
    )

    answered_question_ids = {attempt.question_id for attempt in attempts}
    if not set(question_ids).issubset(answered_question_ids):
        return

    # 计算得分
    correct_count = sum(1 for a in attempts if a.is_correct)
    total_questions = len(question_ids)
    max_score = announcement.max_score or 100.0
    score = round(correct_count / total_questions * max_score, 1) if total_questions > 0 else 0.0

    # 更新或创建 TaskCompletion 记录
    completion = db.query(TaskCompletion).filter(
        TaskCompletion.user_id == user_id,
        TaskCompletion.announcement_id == announcement_id
    ).first()

    if completion:
        completion.score = score
        completion.max_score = max_score
    else:
        completion = TaskCompletion(
            user_id=user_id,
            announcement_id=announcement_id,
            score=score,
            max_score=max_score
        )
        try:
            with db.begin_nested():
                db.add(completion)
                db.flush()
        except IntegrityError:
            completion = db.query(TaskCompletion).filter(
                TaskCompletion.user_id == user_id,
                TaskCompletion.announcement_id == announcement_id,
            ).one()
            completion.score = score
            completion.max_score = max_score

    db.flush()
