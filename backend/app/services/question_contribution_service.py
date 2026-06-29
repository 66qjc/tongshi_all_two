"""公共课程题库贡献记录服务。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import Course, QuestionContributionLog, User
from app.services.question_bank_service import resolve_question_bank_course


def resolve_public_question_course(db: Session, course: Course) -> Course:
    """将公共课程副本解析到源公共课程，私有课程保持不变。"""
    return resolve_question_bank_course(db, course)


def record_question_contribution(
    db: Session,
    public_course: Course,
    operator_id: str,
    operator_role: str,
    action: str,
    question_count: int,
) -> None:
    """记录一次公共题库贡献批次。"""
    if question_count <= 0 or not public_course.is_public:
        return
    operator = db.query(User).filter(User.id == operator_id).first()
    db.add(QuestionContributionLog(
        public_course_id=public_course.id,
        public_course_name=public_course.name,
        operator_id=operator_id,
        operator_name=operator.name if operator else operator_id,
        operator_role=operator.role if operator else operator_role,
        action=action,
        question_count=question_count,
    ))


def list_question_contributions(
    db: Session,
    public_course_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[QuestionContributionLog], int]:
    """分页读取单门公共课程的题库贡献记录。"""
    query = db.query(QuestionContributionLog).filter(
        QuestionContributionLog.public_course_id == public_course_id,
    )
    total = query.count()
    items = query.order_by(
        QuestionContributionLog.created_at.desc(),
        QuestionContributionLog.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size).all()
    return items, total
