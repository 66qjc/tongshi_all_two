"""Task completion service"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Announcement, Class, StudentClassEnrollment, TaskCompletion, User


def mark_completed(db: Session, user_id: str, announcement_id: int):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        return None
    existing = db.query(TaskCompletion).filter(
        TaskCompletion.user_id == user_id,
        TaskCompletion.announcement_id == announcement_id,
    ).first()
    if existing:
        return existing
    try:
        completion = TaskCompletion(user_id=user_id, announcement_id=announcement_id)
        db.add(completion)
        db.commit()
        db.refresh(completion)
        return completion
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "标记完成失败")


def completion_report(db: Session, announcement_id: int):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        return None
    cls = ann.class_
    students = (
        db.query(User)
        .join(StudentClassEnrollment, StudentClassEnrollment.user_id == User.id)
        .filter(StudentClassEnrollment.class_id == ann.class_id, User.role == "student")
        .all()
    )
    completed_ids = {
        row.user_id for row in db.query(TaskCompletion.user_id).filter(TaskCompletion.announcement_id == announcement_id).all()
    }
    incomplete = [{"id": s.id, "name": s.name} for s in students if s.id not in completed_ids]
    return {
        "announcement_id": ann.id,
        "announcement_title": ann.title,
        "class_name": cls.name if cls else "",
        "total_students": len(students),
        "completed_students": len(students) - len(incomplete),
        "incomplete_students": incomplete,
        "is_expired": bool(ann.end_time and datetime.now(timezone.utc) > ann.end_time),
    }
