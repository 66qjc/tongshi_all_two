"""Announcement service"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Announcement, AnnouncementRead, Class, StudentClassEnrollment, User

logger = logging.getLogger(__name__)


def _iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def _announcement_payload(ann: Announcement, current_user_id: str | None = None):
    cls = ann.class_
    teacher = ann.teacher
    is_read = False
    if current_user_id:
        is_read = any(r.user_id == current_user_id for r in ann.reads)
    return {
        "id": ann.id,
        "class_id": ann.class_id,
        "class_name": cls.name if cls else "",
        "teacher_id": ann.teacher_id,
        "teacher_name": teacher.name if teacher else "",
        "type": ann.type,
        "title": ann.title,
        "content": ann.content,
        "question_ids": ann.question_ids or [],
        "start_time": _iso(ann.start_time),
        "end_time": _iso(ann.end_time),
        "created_at": _iso(ann.created_at),
        "is_read": is_read,
    }


def list_announcements(db: Session, current_user):
    if current_user.role == "teacher":
        anns = db.query(Announcement).filter(Announcement.teacher_id == current_user.id).order_by(Announcement.created_at.desc()).all()
        return [_announcement_payload(ann, current_user.id) for ann in anns]

    class_ids = [row.class_id for row in db.query(StudentClassEnrollment.class_id).filter(StudentClassEnrollment.user_id == current_user.id).all()]
    if not class_ids:
        return []
    anns = (
        db.query(Announcement)
        .filter(Announcement.class_id.in_(class_ids))
        .order_by(Announcement.created_at.desc())
        .all()
    )
    return [_announcement_payload(ann, current_user.id) for ann in anns]


def create_announcement(db: Session, teacher_id: str, data: dict):
    cls = db.query(Class).filter(Class.id == data.get("class_id")).first()
    if not cls:
        raise BusinessException(404, "班级不存在")
    ann = Announcement(
        class_id=data["class_id"],
        teacher_id=teacher_id,
        type=data["type"],
        title=data["title"],
        content=data.get("content", ""),
        question_ids=data.get("question_ids") or [],
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
    )
    try:
        db.add(ann)
        db.commit()
        db.refresh(ann)
        logger.info(f"教师发布公告: teacher_id={teacher_id}, class_id={data['class_id']}, type={data['type']}, title={data['title']}")
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "发布失败")
    return ann


def delete_announcement(db: Session, announcement_id: int, teacher_id: str):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id, Announcement.teacher_id == teacher_id).first()
    if not ann:
        return None
    try:
        db.delete(ann)
        db.commit()
        logger.info(f"教师删除公告: teacher_id={teacher_id}, announcement_id={announcement_id}")
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "删除失败")
    return ann


def get_announcement(db: Session, announcement_id: int, current_user):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        return None
    if current_user.role != "teacher":
        class_ids = [row.class_id for row in db.query(StudentClassEnrollment.class_id).filter(StudentClassEnrollment.user_id == current_user.id).all()]
        if ann.class_id not in class_ids:
            raise BusinessException(403, "无权访问")
    return _announcement_payload(ann, current_user.id)


def unread_count(db: Session, user_id: str) -> int:
    class_ids = [row.class_id for row in db.query(StudentClassEnrollment.class_id).filter(StudentClassEnrollment.user_id == user_id).all()]
    if not class_ids:
        return 0
    read_ids = [row.announcement_id for row in db.query(AnnouncementRead.announcement_id).filter(AnnouncementRead.user_id == user_id).all()]
    query = db.query(Announcement).filter(Announcement.class_id.in_(class_ids))
    if read_ids:
        query = query.filter(~Announcement.id.in_(read_ids))
    return query.count()


def mark_read(db: Session, user_id: str, announcement_id: int):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        return None
    existing = db.query(AnnouncementRead).filter(
        AnnouncementRead.user_id == user_id,
        AnnouncementRead.announcement_id == announcement_id,
    ).first()
    if existing:
        return existing
    try:
        read = AnnouncementRead(user_id=user_id, announcement_id=announcement_id)
        db.add(read)
        db.commit()
        db.refresh(read)
        return read
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "标记已读失败")
