"""用户个人通知服务"""
from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import UserNotification


def _format_notification(notification: UserNotification) -> dict:
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "type": notification.type,
        "title": notification.title,
        "content": notification.content or "",
        "related_type": notification.related_type or "",
        "related_id": notification.related_id,
        "is_read": bool(notification.is_read),
        "created_at": notification.created_at.isoformat() if notification.created_at else "",
    }


def create_notification(
    db: Session,
    *,
    user_id: str,
    type_: str,
    title: str,
    content: str = "",
    related_type: str = "",
    related_id: int | None = None,
) -> UserNotification:
    notification = UserNotification(
        user_id=user_id,
        type=type_,
        title=title,
        content=content,
        related_type=related_type,
        related_id=related_id,
        is_read=False,
    )
    db.add(notification)
    return notification


def list_notifications(db: Session, user_id: str) -> list[dict]:
    notifications = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == user_id)
        .order_by(UserNotification.created_at.desc(), UserNotification.id.desc())
        .all()
    )
    return [_format_notification(item) for item in notifications]


def unread_count(db: Session, user_id: str) -> int:
    return (
        db.query(UserNotification)
        .filter(UserNotification.user_id == user_id, UserNotification.is_read.is_(False))
        .count()
    )


def mark_read(db: Session, user_id: str, notification_id: int):
    notification = (
        db.query(UserNotification)
        .filter(UserNotification.id == notification_id, UserNotification.user_id == user_id)
        .first()
    )
    if not notification:
        return None
    if notification.is_read:
        return notification
    try:
        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return notification
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "标记通知已读失败")
