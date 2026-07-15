"""练习与错题本服务。"""
from datetime import datetime, timezone

from sqlalchemy import func as sa_func, case, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BusinessException
from app.core.timezone_utils import beijing_today, to_beijing_iso
from app.models.entities import Announcement, Class, Course, Question, QuizAttempt, StudentClassEnrollment, TaskCompletion
from app.services.access_control_service import (
    student_can_access_course,
    student_has_active_course_enrollment,
)
from app.services.task_service import get_accessible_assignment, validate_assignment_available


def _active_question_query(db: Session):
    """仅查询未软删题目及其所属活跃课程。"""
    return (
        db.query(Question)
        .join(Course, Course.id == Question.course_id)
        .filter(Question.deleted_at.is_(None), Course.deleted_at.is_(None))
    )


def _student_can_access_question(db: Session, user_id: str, question: Question) -> bool:
    """学生自由练习可见范围：活跃选课 + 公共共享题库（公共课挂载题）。

    - 私有课题目：仅当学生加入该题所属活跃课程时可见
    - 公共课题目：任一活跃选课学生可练（全站共享题库）
    - 题目或所属课程已软删：不可见
    """
    if question.deleted_at is not None:
        return False
    course = db.query(Course).filter(
        Course.id == question.course_id,
        Course.deleted_at.is_(None),
    ).first()
    if not course:
        return False
    if course.is_public:
        return student_has_active_course_enrollment(db, user_id)
    return student_can_access_course(db, user_id, question.course_id)


def submit_answer(
    db: Session,
    user_id: str,
    question_id: int,
    user_answer: str,
    role: str = "student",
    announcement_id: int | None = None,
):
    question = _active_question_query(db).filter(Question.id == question_id).first()
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
        elif not _student_can_access_question(db, user_id, question):
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


def _student_active_course_ids(db: Session, user_id: str) -> list[int]:
    """学生已加入的活跃课程 ID 列表（排除软删班级/课程）。"""
    rows = (
        db.query(Class.course_id)
        .join(StudentClassEnrollment, StudentClassEnrollment.class_id == Class.id)
        .join(Course, Course.id == Class.course_id)
        .filter(
            StudentClassEnrollment.user_id == user_id,
            Class.deleted_at.is_(None),
            Course.deleted_at.is_(None),
            Class.course_id.isnot(None),
        )
        .distinct()
        .all()
    )
    return [row.course_id for row in rows if row.course_id is not None]


def _visible_question_ids_for_student(db: Session, user_id: str):
    """学生自由练习可见题目：所属活跃私有课 或 全站公共课挂载题。"""
    if not student_has_active_course_enrollment(db, user_id):
        return db.query(Question.id).filter(False)
    student_course_ids = _student_active_course_ids(db, user_id)
    return (
        db.query(Question.id)
        .join(Course, Course.id == Question.course_id)
        .filter(
            Question.deleted_at.is_(None),
            Course.deleted_at.is_(None),
            or_(Course.is_public.is_(True), Question.course_id.in_(student_course_ids)),
        )
    )


def get_quiz_stats(db: Session, user_id: str):
    visible_question_ids = _visible_question_ids_for_student(db, user_id)
    total_questions = (
        db.query(Question)
        .filter(Question.id.in_(visible_question_ids))
        .count()
    )
    if total_questions == 0 and not student_has_active_course_enrollment(db, user_id):
        return {
            "total_questions": 0,
            "questions_done": 0,
            "accuracy": 0,
            "today_count": 0,
        }

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
        QuizAttempt.question_id.in_(visible_question_ids),
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

    # 课程入口仅校验活跃选课；统计范围对齐自由练习可见题（含公共共享题库）。
    visible_question_ids = _visible_question_ids_for_student(db, user_id)
    row = db.query(
        sa_func.count(QuizAttempt.id).label("done"),
        sa_func.sum(
            case((QuizAttempt.is_correct == True, 1), else_=0)  # noqa: E712
        ).label("correct"),
    ).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.announcement_id.is_(None),
        QuizAttempt.question_id.in_(visible_question_ids),
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
    """每道题取最近一次答题记录，仅保留仍答错且当前仍可见的题。"""
    from sqlalchemy import func as sa_func

    if not student_has_active_course_enrollment(db, user_id):
        return []

    visible_question_ids = _visible_question_ids_for_student(db, user_id)
    student_course_ids = _student_active_course_ids(db, user_id)

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
        .filter(Question.id.in_(visible_question_ids))
        .options(joinedload(QuizAttempt.question))
        .all()
    )

    course_ids_for_names = set(student_course_ids)
    for a in attempts:
        if a.question and a.question.course_id is not None:
            course_ids_for_names.add(a.question.course_id)
    courses = (
        db.query(Course)
        .filter(Course.id.in_(course_ids_for_names), Course.deleted_at.is_(None))
        .all()
        if course_ids_for_names
        else []
    )
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
