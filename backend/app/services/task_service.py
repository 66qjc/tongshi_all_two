"""题目任务完成服务。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Announcement, AnnouncementClass, StudentClassEnrollment, TaskCompletion, User


def _student_can_access(db: Session, user_id: str, announcement_id: int) -> bool:
    class_ids = [
        row.class_id for row in db.query(StudentClassEnrollment.class_id)
        .filter(StudentClassEnrollment.user_id == user_id)
        .all()
    ]
    if not class_ids:
        return False
    return db.query(AnnouncementClass).filter(
        AnnouncementClass.announcement_id == announcement_id,
        AnnouncementClass.class_id.in_(class_ids),
    ).first() is not None


def mark_completed(db: Session, user_id: str, announcement_id: int):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann or not _student_can_access(db, user_id, announcement_id):
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


def completion_report(db: Session, announcement_id: int, teacher_id: str):
    ann = db.query(Announcement).filter(
        Announcement.id == announcement_id,
        Announcement.teacher_id == teacher_id,
    ).first()
    if not ann:
        return None

    class_links = db.query(AnnouncementClass).filter(AnnouncementClass.announcement_id == announcement_id).all()
    class_ids = [link.class_id for link in class_links]
    students = (
        db.query(User, StudentClassEnrollment.class_id)
        .join(StudentClassEnrollment, StudentClassEnrollment.user_id == User.id)
        .filter(StudentClassEnrollment.class_id.in_(class_ids), User.role == "student")
        .all()
    )
    completed_ids = {
        row.user_id for row in db.query(TaskCompletion.user_id)
        .filter(TaskCompletion.announcement_id == announcement_id)
        .all()
    }

    class_name_by_id = {
        link.class_id: link.class_.name if link.class_ else ""
        for link in class_links
    }
    seen_student_ids: set[str] = set()
    completed_students = []
    incomplete_students = []
    per_class = []

    for class_id in class_ids:
        class_students = [(student, cid) for student, cid in students if cid == class_id]
        class_completed = 0
        for student, _ in class_students:
            payload = {"id": student.id, "name": student.name, "class_id": class_id, "class_name": class_name_by_id.get(class_id, "")}
            if student.id in completed_ids:
                class_completed += 1
                if student.id not in seen_student_ids:
                    completed_students.append(payload)
            elif student.id not in seen_student_ids:
                incomplete_students.append(payload)
            seen_student_ids.add(student.id)
        per_class.append({
            "class_id": class_id,
            "class_name": class_name_by_id.get(class_id, ""),
            "total": len(class_students),
            "completed": class_completed,
        })

    return {
        "announcement_id": ann.id,
        "announcement_title": ann.title,
        "course_id": ann.course_id,
        "class_names": [class_name_by_id.get(class_id, "") for class_id in class_ids],
        "total_students": len(seen_student_ids),
        "completed_students": completed_students,
        "completed_count": len(completed_students),
        "incomplete_students": incomplete_students,
        "per_class": per_class,
        "is_expired": bool(ann.end_time and datetime.now(timezone.utc) > ann.end_time),
    }
