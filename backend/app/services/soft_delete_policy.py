"""Fixed retention and restore policies for the seven soft-deletable resources."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.exceptions import BusinessException
from app.core.timezone_utils import BEIJING_TZ


@dataclass(frozen=True)
class ResourcePolicy:
    """The immutable business policy for one resource type."""

    display_name: str
    retention_unit: str
    retention_value: int
    cascade_children: tuple[str, ...]
    restore_mode: str

    @property
    def chinese_name(self) -> str:
        return self.display_name

    @property
    def retention_days(self) -> int | None:
        return self.retention_value if self.retention_unit == "days" else None


RESOURCE_POLICIES: dict[str, ResourcePolicy] = {
    "users": ResourcePolicy("用户", "days", 30, (), "self"),
    "courses": ResourcePolicy(
        "课程", "days", 30, ("classes", "materials", "announcements"), "same_batch"
    ),
    "classes": ResourcePolicy("班级", "days", 30, (), "self"),
    "announcements": ResourcePolicy("作业", "days", 30, (), "self"),
    "projects": ResourcePolicy("作品", "months", 6, (), "self"),
    "materials": ResourcePolicy("资料", "months", 6, (), "self"),
    "questions": ResourcePolicy("题目", "months", 6, (), "self"),
}


def get_resource_policy(resource_type: str) -> ResourcePolicy:
    try:
        return RESOURCE_POLICIES[resource_type]
    except KeyError as exc:
        raise BusinessException(400, "不支持的资源类型") from exc


def retention_deadline(deleted_at: datetime, resource_type: str) -> datetime:
    """Return the Beijing-time retention deadline for a deleted resource."""

    policy = get_resource_policy(resource_type)
    if deleted_at.tzinfo is None:
        deleted_at = deleted_at.replace(tzinfo=timezone.utc)
    local_deleted_at = deleted_at.astimezone(BEIJING_TZ)
    if policy.retention_unit == "days":
        return local_deleted_at + timedelta(days=policy.retention_value)

    month_index = local_deleted_at.year * 12 + local_deleted_at.month - 1
    month_index += policy.retention_value
    year, month_offset = divmod(month_index, 12)
    month = month_offset + 1
    day = min(local_deleted_at.day, calendar.monthrange(year, month)[1])
    return local_deleted_at.replace(year=year, month=month, day=day)
