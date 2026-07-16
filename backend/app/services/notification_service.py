"""Student notification service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from string import Template
from typing import Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.timezone_utils import to_beijing_iso
from app.models.entities import Announcement, AnnouncementClass, Class, NotificationPreference, NotificationTemplate, Project, StudentClassEnrollment, StudentNotification, User
from app.schemas.common import AuthUser, NotificationBatchSendIn, NotificationPreferenceIn, NotificationSendIn

PREFERENCE_BY_TYPE = {
    "assignment_published": "enable_assignment_due",
    "assignment_due_soon": "enable_assignment_due",
    "assignment_overdue": "enable_assignment_due",
    "assignment_graded": "enable_grade_published",
    "grade_published": "enable_grade_published",
    "grade_changed": "enable_grade_published",
    "course_material_added": "enable_course_update",
    "course_announcement": "enable_course_update",
    "project_approved": "enable_project_review",
    "project_rejected": "enable_project_review",
    "project_review": "enable_project_review",
}


DEFAULT_NOTIFICATION_TEMPLATES = [
    {
        "code": "assignment_due_soon",
        "category": "assignment",
        "title_template": "作业《$title》即将截止",
        "content_template": "请及时完成作业，避免错过截止时间。",
        "action_url_template": "/practice/announcement/$announcement_id",
    },
    {
        "code": "grade_published",
        "category": "grade",
        "title_template": "成绩已发布",
        "content_template": "你有新的成绩通知，请及时查看。",
        "action_url_template": "/profile",
    },
    {
        "code": "course_material_added",
        "category": "course",
        "title_template": "课程资料已更新",
        "content_template": "课程《$course_name》新增了学习资料。",
        "action_url_template": "/learn/course/$course_id",
    },
    {
        "code": "project_rejected",
        "category": "project",
        "title_template": "作品《$project_title》审核未通过",
        "content_template": "$reason",
        "action_url_template": "/projects/$project_id",
    },
]


def _format_notification(item: StudentNotification) -> dict:
    return {
        "id": item.id,
        "type": item.type,
        "category": item.category or "project",
        "priority": item.priority or "normal",
        "title": item.title,
        "content": item.content or "",
        "project_id": item.project_id,
        "action_url": item.action_url or "",
        "extra_data": item.extra_data or {},
        "expires_at": to_beijing_iso(item.expires_at),
        "sent_at": to_beijing_iso(item.sent_at),
        "is_read": bool(item.is_read),
        "created_at": to_beijing_iso(item.created_at),
    }


def get_or_create_preferences(db: Session, user_id: str) -> NotificationPreference:
    """读取或创建学生通知偏好。"""
    pref = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
    if pref:
        return pref
    user = db.query(User).filter(User.id == user_id, User.role == "student").first()
    if not user:
        raise BusinessException(404, "学生不存在")
    pref = NotificationPreference(user_id=user_id)
    db.add(pref)
    db.flush()
    return pref


def format_preferences(pref: NotificationPreference) -> dict:
    return {
        "user_id": pref.user_id,
        "enable_assignment_due": bool(pref.enable_assignment_due),
        "enable_grade_published": bool(pref.enable_grade_published),
        "enable_course_update": bool(pref.enable_course_update),
        "enable_project_review": bool(pref.enable_project_review),
        "updated_at": to_beijing_iso(pref.updated_at),
    }


def update_preferences(db: Session, user_id: str, data: NotificationPreferenceIn) -> dict:
    """更新学生通知偏好。"""
    pref = get_or_create_preferences(db, user_id)
    for field in [
        "enable_assignment_due",
        "enable_grade_published",
        "enable_course_update",
        "enable_project_review",
    ]:
        value = getattr(data, field)
        if value is not None:
            setattr(pref, field, value)
    db.commit()
    db.refresh(pref)
    return format_preferences(pref)


def _preference_allows(db: Session, user_id: str, notification_type: str) -> bool:
    field = PREFERENCE_BY_TYPE.get(notification_type)
    if not field:
        return True
    pref = get_or_create_preferences(db, user_id)
    return bool(getattr(pref, field))


def list_notifications(db: Session, user_id: str, category: str | None = None, unread_only: bool = False) -> list[dict]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    query = db.query(StudentNotification).filter(
        StudentNotification.user_id == user_id,
        or_(StudentNotification.expires_at.is_(None), StudentNotification.expires_at > now),
    )
    if category:
        query = query.filter(StudentNotification.category == category)
    if unread_only:
        query = query.filter(StudentNotification.is_read.is_(False))
    items = query.order_by(StudentNotification.created_at.desc(), StudentNotification.id.desc()).all()
    return [_format_notification(item) for item in items]


def unread_count(db: Session, user_id: str) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return (
        db.query(StudentNotification)
        .filter(
            StudentNotification.user_id == user_id,
            StudentNotification.is_read.is_(False),
            or_(StudentNotification.expires_at.is_(None), StudentNotification.expires_at > now),
        )
        .count()
    )


def mark_read(db: Session, notification_id: int, user_id: str) -> StudentNotification | None:
    item = (
        db.query(StudentNotification)
        .filter(StudentNotification.id == notification_id, StudentNotification.user_id == user_id)
        .first()
    )
    if not item:
        return None
    if not item.is_read:
        item.is_read = True
        db.commit()
        db.refresh(item)
    return item


def mark_all_read(db: Session, user_id: str) -> int:
    """将学生全部通知标记已读。"""
    updated = (
        db.query(StudentNotification)
        .filter(StudentNotification.user_id == user_id, StudentNotification.is_read.is_(False))
        .update({StudentNotification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return updated


def _accessible_student_ids(db: Session, operator: AuthUser, user_ids: Iterable[str]) -> set[str]:
    """返回当前操作人有权通知的未删除学生 ID。"""
    requested_ids = set(user_ids)
    if not requested_ids:
        return set()

    query = db.query(User.id).filter(
        User.id.in_(requested_ids),
        User.role == "student",
        User.deleted_at.is_(None),
    )
    if operator.role == "teacher":
        query = (
            query.join(StudentClassEnrollment, StudentClassEnrollment.user_id == User.id)
            .join(Class, Class.id == StudentClassEnrollment.class_id)
            .filter(
                Class.created_by == operator.id,
                Class.deleted_at.is_(None),
            )
        )
    elif operator.role != "admin":
        raise BusinessException(403, "无权执行此操作")

    return {row[0] for row in query.distinct().all()}


def send_notification(db: Session, data: NotificationSendIn, operator: AuthUser) -> dict:
    """仅向当前操作人有权管理的未删除学生发送单条通知。"""
    accessible_ids = _accessible_student_ids(db, operator, [data.user_id])
    if data.user_id not in accessible_ids:
        if operator.role == "teacher":
            raise BusinessException(403, "无权向该学生发送通知")
        raise BusinessException(404, "学生不存在")
    if not _preference_allows(db, data.user_id, data.type):
        db.commit()
        return {"sent_count": 0, "skipped_count": 1, "notification_ids": []}
    item = StudentNotification(
        user_id=data.user_id,
        type=data.type,
        category=data.category,
        priority=data.priority,
        title=data.title,
        content=data.content,
        action_url=data.action_url,
        extra_data=data.extra_data,
        expires_at=data.expires_at,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"sent_count": 1, "skipped_count": 0, "notification_ids": [item.id]}


def send_batch_notifications(db: Session, data: NotificationBatchSendIn, operator: AuthUser) -> dict:
    """批量过滤无权访问、已删除或偏好关闭的学生并返回发送/跳过数量。"""
    sent_ids: list[int] = []
    skipped = 0
    accessible_ids = _accessible_student_ids(db, operator, data.user_ids)
    for user_id in data.user_ids:
        payload = NotificationSendIn(
            user_id=user_id,
            type=data.type,
            title=data.title,
            content=data.content,
            category=data.category,
            priority=data.priority,
            action_url=data.action_url,
            extra_data=data.extra_data,
            expires_at=data.expires_at,
        )
        if user_id not in accessible_ids or not _preference_allows(db, user_id, data.type):
            skipped += 1
            continue
        item = StudentNotification(
            user_id=user_id,
            type=payload.type,
            category=payload.category,
            priority=payload.priority,
            title=payload.title,
            content=payload.content,
            action_url=payload.action_url,
            extra_data=payload.extra_data,
            expires_at=payload.expires_at,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(item)
        db.flush()
        sent_ids.append(item.id)
    db.commit()
    return {"sent_count": len(sent_ids), "skipped_count": skipped, "notification_ids": sent_ids}



def _student_ids_for_announcement(db: Session, announcement_id: int) -> list[str]:
    """查询公告关联班级中的学生 ID 列表。"""
    rows = (
        db.query(StudentClassEnrollment.user_id)
        .join(AnnouncementClass, AnnouncementClass.class_id == StudentClassEnrollment.class_id)
        .join(User, User.id == StudentClassEnrollment.user_id)
        .filter(
            AnnouncementClass.announcement_id == announcement_id,
            User.role == "student",
            User.deleted_at.is_(None),
        )
        .distinct()
        .all()
    )
    return sorted(row[0] for row in rows)


def send_assignment_due_soon_reminders(
    db: Session,
    *,
    now: datetime | None = None,
    window_hours: int = 24,
) -> dict:
    """发送即将截止的作业提醒，供外部定时任务调用。"""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is not None:
        current = current.replace(tzinfo=None)
    window_end = current + timedelta(hours=window_hours)
    announcements = (
        db.query(Announcement)
        .filter(
            Announcement.deleted_at.is_(None),
            Announcement.end_time.isnot(None),
            Announcement.end_time >= current,
            Announcement.end_time <= window_end,
        )
        .order_by(Announcement.end_time.asc(), Announcement.id.asc())
        .all()
    )
    sent_ids: list[int] = []
    skipped = 0
    for ann in announcements:
        action_url = f"/practice/announcement/{ann.id}"
        for user_id in _student_ids_for_announcement(db, ann.id):
            exists = db.query(StudentNotification).filter(
                StudentNotification.user_id == user_id,
                StudentNotification.type == "assignment_due_soon",
                StudentNotification.action_url == action_url,
            ).first()
            if exists:
                skipped += 1
                continue
            if not _preference_allows(db, user_id, "assignment_due_soon"):
                skipped += 1
                continue
            item = StudentNotification(
                user_id=user_id,
                type="assignment_due_soon",
                category="assignment",
                priority="high",
                title=f"作业《{ann.title}》即将截止",
                content="请及时完成作业，避免错过截止时间。",
                action_url=action_url,
                extra_data={"announcement_id": ann.id, "course_id": ann.course_id},
                sent_at=datetime.now(timezone.utc),
            )
            db.add(item)
            db.flush()
            sent_ids.append(item.id)
    db.commit()
    return {"sent_count": len(sent_ids), "skipped_count": skipped, "notification_ids": sent_ids}



def ensure_default_notification_templates(db: Session) -> int:
    """初始化系统默认通知模板。"""
    created = 0
    for item in DEFAULT_NOTIFICATION_TEMPLATES:
        exists = db.query(NotificationTemplate).filter(NotificationTemplate.code == item["code"]).first()
        if exists:
            continue
        db.add(NotificationTemplate(**item))
        created += 1
    if created:
        db.commit()
    return created


def cleanup_read_expired_notifications(db: Session, *, now: datetime | None = None) -> dict:
    """删除已读且已过期的通知，供外部定时任务调用。"""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is not None:
        current = current.replace(tzinfo=None)
    rows = db.query(StudentNotification).filter(
        StudentNotification.is_read.is_(True),
        StudentNotification.expires_at.isnot(None),
        StudentNotification.expires_at <= current,
    ).all()
    deleted_count = len(rows)
    for item in rows:
        db.delete(item)
    if deleted_count:
        db.commit()
    return {"deleted_count": deleted_count}


def render_template(template: NotificationTemplate, variables: dict[str, str]) -> dict:
    """渲染通知模板。"""
    return {
        "title": Template(template.title_template).safe_substitute(variables),
        "content": Template(template.content_template or "").safe_substitute(variables),
        "action_url": Template(template.action_url_template or "").safe_substitute(variables),
    }


def create_project_review_notification(db: Session, project: Project, approved: bool, reason: str = "") -> None:
    status_text = "审核通过" if approved else "审核驳回"
    title = f"作品《{project.title}》{status_text}"
    if approved:
        content = "你的作品已通过教师审核，可以在作品展示中查看。"
        notification_type = "project_approved"
    else:
        detail = reason.strip() if reason else "请根据教师反馈修改后重新提交。"
        content = f"你的作品未通过审核，驳回原因：{detail}"
        notification_type = "project_rejected"

    db.add(StudentNotification(
        user_id=project.author_id,
        type=notification_type,
        category="project",
        priority="normal",
        title=title,
        content=content,
        project_id=project.id,
        action_url=f"/create/project/{project.id}",
        sent_at=datetime.now(timezone.utc),
    ))
