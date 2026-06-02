"""发布题目服务。"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import (
    Announcement,
    AnnouncementClass,
    AnnouncementRead,
    Class,
    Course,
    Question,
    StudentClassEnrollment,
    User,
)

logger = logging.getLogger(__name__)


def _iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def _class_payloads(ann: Announcement) -> list[dict]:
    return [
        {"id": item.class_id, "name": item.class_.name if item.class_ else ""}
        for item in ann.target_classes
    ]


def _announcement_payload(ann: Announcement, current_user_id: str | None = None):
    teacher = ann.teacher
    is_read = False
    if current_user_id:
        is_read = any(r.user_id == current_user_id for r in ann.reads)
    classes = _class_payloads(ann)
    return {
        "id": ann.id,
        "course_id": ann.course_id,
        "course_name": ann.course.name if ann.course else "",
        "class_ids": [item["id"] for item in classes],
        "class_names": [item["name"] for item in classes],
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
        .join(AnnouncementClass, AnnouncementClass.announcement_id == Announcement.id)
        .filter(AnnouncementClass.class_id.in_(class_ids))
        .order_by(Announcement.created_at.desc())
        .distinct()
        .all()
    )
    return [_announcement_payload(ann, current_user.id) for ann in anns]


def create_announcement(db: Session, teacher_id: str, data: dict):
    course_id = data.get("course_id")
    class_ids = data.get("class_ids") or []
    question_ids = data.get("question_ids") or []
    if not class_ids:
        raise BusinessException(400, "请选择目标班级")
    if not question_ids:
        raise BusinessException(400, "请选择题目")

    course = db.query(Course).filter(
        Course.id == course_id,
        or_(Course.created_by == teacher_id, Course.is_public.is_(True)),
    ).first()
    if not course:
        raise BusinessException(404, "课程不存在")

    classes = db.query(Class).filter(
        Class.id.in_(class_ids),
        Class.course_id == course_id,
        Class.created_by == teacher_id,
    ).all()
    if len(classes) != len(set(class_ids)):
        raise BusinessException(400, "目标班级必须属于所选课程")

    questions = db.query(Question).filter(Question.id.in_(question_ids), Question.course_id == course_id).all()
    if len(questions) != len(set(question_ids)):
        raise BusinessException(400, "题目必须属于所选课程")

    ann = Announcement(
        course_id=course_id,
        teacher_id=teacher_id,
        type="quiz",
        title=data["title"],
        content="",
        question_ids=question_ids,
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
    )
    try:
        db.add(ann)
        db.flush()
        for class_id in sorted(set(class_ids)):
            db.add(AnnouncementClass(announcement_id=ann.id, class_id=class_id))
        db.commit()
        db.refresh(ann)
        logger.info(f"教师发布题目: teacher_id={teacher_id}, course_id={course_id}, title={data['title']}")
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
        logger.info(f"教师删除发布题目: teacher_id={teacher_id}, announcement_id={announcement_id}")
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "删除失败")
    return ann


def get_announcement(db: Session, announcement_id: int, current_user):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        return None
    if current_user.role == "teacher":
        if ann.teacher_id != current_user.id:
            raise BusinessException(403, "无权访问")
    else:
        class_ids = [row.class_id for row in db.query(StudentClassEnrollment.class_id).filter(StudentClassEnrollment.user_id == current_user.id).all()]
        ann_class_ids = [row.class_id for row in db.query(AnnouncementClass.class_id).filter(AnnouncementClass.announcement_id == announcement_id).all()]
        if not set(class_ids).intersection(ann_class_ids):
            raise BusinessException(403, "无权访问")
    return _announcement_payload(ann, current_user.id)


def unread_count(db: Session, user_id: str) -> int:
    class_ids = [row.class_id for row in db.query(StudentClassEnrollment.class_id).filter(StudentClassEnrollment.user_id == user_id).all()]
    if not class_ids:
        return 0
    read_ids = [row.announcement_id for row in db.query(AnnouncementRead.announcement_id).filter(AnnouncementRead.user_id == user_id).all()]
    query = (
        db.query(Announcement)
        .join(AnnouncementClass, AnnouncementClass.announcement_id == Announcement.id)
        .filter(AnnouncementClass.class_id.in_(class_ids))
    )
    if read_ids:
        query = query.filter(~Announcement.id.in_(read_ids))
    return query.distinct().count()


def mark_read(db: Session, user_id: str, announcement_id: int):
    ann = get_announcement(db, announcement_id, type("CurrentUser", (), {"id": user_id, "role": "student"})())
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
