"""用户个人通知路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.response import success
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import AuthUser
from app.services.notification_service import (
    list_notifications,
    mark_read,
    unread_count,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", summary="个人通知列表", description="返回当前用户的个人通知")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success(list_notifications(db, current_user.id))


@router.get("/unread-count", summary="个人通知未读数", description="返回当前用户的个人通知未读数量")
def get_notification_unread_count(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success({"count": unread_count(db, current_user.id)})


@router.post("/{notification_id}/read", summary="标记个人通知已读", description="将指定个人通知标记为已读")
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    notification = mark_read(db, current_user.id, notification_id)
    if not notification:
        raise BusinessException(404, "通知不存在")
    return success()
