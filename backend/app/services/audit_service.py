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
        error_message=error_message,
    )
    db.add(log)
    return log


def _format_log(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "user_role": log.user_role,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "resource_name": log.resource_name,
        "details": log.details or {},
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "status": log.status,
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
    ws.append(["时间", "操作人", "角色", "动作", "资源类型", "资源ID", "资源名称", "状态", "错误信息"])
    for log in logs:
        ws.append([
            to_beijing_iso(log.created_at),
            log.user_id or "",
            log.user_role or "",
            log.action,
            log.resource_type or "",
            log.resource_id or "",
            log.resource_name or "",
            log.status,
            log.error_message or "",
        ])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue(), len(logs)
