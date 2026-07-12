"""Student notification routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.response import success
from app.core.security import require_role, require_roles
from app.db.session import get_db
from app.schemas.common import AuthUser, NotificationBatchSendIn, NotificationPreferenceIn, NotificationSendIn
from app.services.notification_service import (
    format_preferences,
    get_or_create_preferences,
    list_notifications,
    mark_all_read,
    mark_read,
    send_batch_notifications,
    send_notification,
    unread_count,
    update_preferences,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", summary="学生通知列表")
def get_notifications(
    category: str | None = None,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    return success(list_notifications(db, current_user.id, category=category, unread_only=unread_only))


@router.post("/send", summary="发送通知")
def post_notification(
    data: NotificationSendIn,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("teacher", "admin")),
):
    return success(send_notification(db, data, current_user))


@router.post("/send-batch", summary="批量发送通知")
def post_batch_notification(
    data: NotificationBatchSendIn,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles("teacher", "admin")),
):
    return success(send_batch_notifications(db, data, current_user))


@router.get("/unread-count", summary="学生未读通知数")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    return success({"count": unread_count(db, current_user.id)})


@router.get("/preferences", summary="获取通知偏好设置")
def get_preferences(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    pref = get_or_create_preferences(db, current_user.id)
    db.commit()
    db.refresh(pref)
    return success(format_preferences(pref))


@router.put("/preferences", summary="更新通知偏好设置")
def put_preferences(
    data: NotificationPreferenceIn,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    return success(update_preferences(db, current_user.id, data))


@router.post("/read-all", summary="全部通知标记已读")
def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    return success({"updated_count": mark_all_read(db, current_user.id)})


@router.post("/{notification_id}/read", summary="标记学生通知已读")
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("student")),
):
    item = mark_read(db, notification_id, current_user.id)
    if not item:
        raise BusinessException(404, "通知不存在")
    return success()
