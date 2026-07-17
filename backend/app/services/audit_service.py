"""审计日志服务。"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from sqlalchemy.orm import Query, Session

from app.core.timezone_utils import to_beijing_iso
from app.models.entities import AuditLog
from app.schemas.common import AuthUser


ACTION_LABELS: dict[str, str] = {
    "course.delete": "删除课程",
    "course.restore": "恢复课程",
    "class.delete": "删除班级",
    "class.restore": "恢复班级",
    "announcement.delete": "删除作业",
    "announcement.restore": "恢复作业",
    "material.delete": "删除资料",
    "material.restore": "恢复资料",
    "project.delete": "删除作品",
    "project.restore": "恢复作品",
    "question.create": "创建题目",
    "question.update": "更新题目",
    "question.delete": "删除题目",
    "question.restore": "恢复题目",
    "user.delete": "删除用户",
    "user.restore": "恢复用户",
    "user.password_reset": "重置用户密码",
    "teacher.create": "创建教师",
    "teacher.delete": "删除教师",
    "teacher.reset_password": "重置教师密码",
    "audit_log.export": "导出审计日志",
    "system.soft_delete_cleanup": "系统自动清理",
    "password_reset.approve": "通过密码重置",
    "password_reset.reject": "驳回密码重置",
}

RESOURCE_TYPE_LABELS: dict[str, str] = {
    "users": "用户",
    "courses": "课程",
    "classes": "班级",
    "announcements": "作业",
    "projects": "作品",
    "materials": "资料",
    "questions": "题目",
    "audit_logs": "审计日志",
}

STATUS_LABELS: dict[str, str] = {
    "success": "成功",
    "failed": "失败",
    "error": "错误",
}


def action_name(action: str | None) -> str:
    """将内部动作代码映射为中文展示名。"""
    if not action:
        return ""
    if action in ACTION_LABELS:
        return ACTION_LABELS[action]
    # 兼容未登记动作：resource.action → 中文资源 + 动作
    if "." in action:
        resource, verb = action.split(".", 1)
        resource_label = RESOURCE_TYPE_LABELS.get(resource, resource)
        verb_map = {
            "delete": "删除",
            "restore": "恢复",
            "create": "创建",
            "update": "更新",
            "export": "导出",
            "purge": "彻底删除",
        }
        return f"{verb_map.get(verb, verb)}{resource_label}"
    return action


def resource_type_name(resource_type: str | None) -> str:
    if not resource_type:
        return ""
    return RESOURCE_TYPE_LABELS.get(resource_type, resource_type)


def status_name(status: str | None) -> str:
    if not status:
        return ""
    return STATUS_LABELS.get(status, status)


def create_audit_log(
    db: Session,
    *,
    user: AuthUser | None = None,
    user_id: str | None = None,
    user_role: str | None = None,
    action: str,
    resource_type: str | None = None,
    resource_id: int | str | None = None,
    resource_name: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    status: str = "success",
    error_message: str | None = None,
) -> AuditLog:
    """创建审计日志，调用方负责提交事务。"""
    # error_message 列最长 512；长堆栈只截断入库，完整原因可放 details
    safe_error = error_message
    if safe_error is not None and len(safe_error) > 512:
        safe_error = safe_error[:509] + "..."
    log = AuditLog(
        user_id=user.id if user else user_id,
        user_role=user.role if user else user_role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        resource_name=resource_name,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        error_message=safe_error,
    )
    db.add(log)
    return log


def _format_log(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "user_role": log.user_role,
        "action": log.action,
        "action_name": action_name(log.action),
        "resource_type": log.resource_type,
        "resource_type_name": resource_type_name(log.resource_type),
        "resource_id": log.resource_id,
        "resource_name": log.resource_name,
        "details": log.details or {},
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "status": log.status,
        "status_name": status_name(log.status),
        "error_message": log.error_message,
        "created_at": to_beijing_iso(log.created_at),
    }


def _apply_audit_filters(
    query: Query,
    *,
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: int | str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Query:
    """按审计日志查询条件追加过滤。"""
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id is not None and str(resource_id) != "":
        query = query.filter(AuditLog.resource_id == str(resource_id))
    if status:
        query = query.filter(AuditLog.status == status)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    return query


def query_audit_logs(
    db: Session,
    *,
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: int | str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询审计日志。"""
    safe_page = max(page or 1, 1)
    safe_page_size = max(min(page_size or 20, 100), 1)
    query = _apply_audit_filters(
        db.query(AuditLog),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    total = query.count()
    items = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {
        "items": [_format_log(item) for item in items],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def export_audit_logs(
    db: Session,
    *,
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: int | str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 5000,
) -> tuple[bytes, int]:
    """按筛选条件导出审计日志 Excel，并返回导出条数。"""
    query = _apply_audit_filters(
        db.query(AuditLog),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    logs = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "审计日志"
    ws.append([
        "时间",
        "操作人",
        "角色",
        "动作代码",
        "动作名称",
        "资源类型",
        "资源类型名称",
        "资源ID",
        "资源名称",
        "状态",
        "状态名称",
        "错误信息",
    ])
    for log in logs:
        ws.append([
            to_beijing_iso(log.created_at),
            log.user_id or "",
            log.user_role or "",
            log.action,
            action_name(log.action),
            log.resource_type or "",
            resource_type_name(log.resource_type),
            log.resource_id or "",
            log.resource_name or "",
            log.status,
            status_name(log.status),
            log.error_message or "",
        ])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue(), len(logs)
