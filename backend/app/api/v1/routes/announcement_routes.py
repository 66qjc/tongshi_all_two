"""Announcement routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, AnnouncementCreate
from app.services.announcement_service import (
    list_announcements, create_announcement, delete_announcement,
    unread_count, mark_read, get_announcement,
)
from app.services.task_service import mark_completed, completion_report, task_overview

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("", summary="获取发布题目列表", description="教师：自己发布的题目；学生：所在班级的题目任务（含已读/未读状态）")
def get_list(db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    return success(list_announcements(db, current_user))


@router.post("", summary="发布题目", description="教师端：向一个或多个班级发布题目")
def create(data: AnnouncementCreate, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    ann = create_announcement(db, current_user.id, data.model_dump())
    return success({"id": ann.id})


@router.delete("/{announcement_id}", summary="删除发布题目", description="教师端：删除自己发布的题目及所有关联数据")
def remove(announcement_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    ann = delete_announcement(db, announcement_id, current_user.id)
    if not ann:
        raise BusinessException(404, "发布题目不存在")
    return success()


@router.get("/unread-count", summary="获取未读题目数", description="学生端：返回当前学生所在班级的未读题目数量")
def get_unread_count(db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("student"))):
    return success({"count": unread_count(db, current_user.id)})


@router.get("/task-overview", summary="任务总览", description="教师端：返回所有任务的总体完成/未完成统计及每个任务的简要信息")
def overview(db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    return success(task_overview(db, current_user.id))


@router.post("/{announcement_id}/read", summary="标记题目已读", description="学生端：将指定题目任务标记为已读（幂等）")
def read(announcement_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("student"))):
    ann = mark_read(db, current_user.id, announcement_id)
    if not ann:
        raise BusinessException(404, "题目任务不存在")
    return success()


@router.get("/{announcement_id}", summary="获取题目任务详情", description="返回题目任务的完整信息，含班级名、教师名、已读状态，学生只能查看本班任务")
def detail(announcement_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    ann = get_announcement(db, announcement_id, current_user)
    if not ann:
        raise BusinessException(404, "题目任务不存在")
    return success(ann)


@router.post("/{announcement_id}/complete", summary="标记任务完成", description="学生端：标记题目任务为已完成（幂等）")
def complete(announcement_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("student"))):
    completion = mark_completed(db, current_user.id, announcement_id)
    if not completion:
        raise BusinessException(404, "题目任务不存在")
    return success()


@router.get("/{announcement_id}/completion-report", summary="获取完成报告", description="教师端：查询指定任务的完成统计（已完成/未完成学生列表 + 是否超时）")
def report(announcement_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    data = completion_report(db, announcement_id, current_user.id)
    if not data:
        raise BusinessException(404, "题目任务不存在")
    return success(data)
