"""软删除到期快照与物理清理服务。"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.timezone_utils import BEIJING_TZ
from app.models.entities import (
    Announcement,
    AnnouncementClass,
    AnnouncementRead,
    Class,
    Course,
    HistorySnapshot,
    Material,
    MaterialPreview,
    Project,
    ProjectImage,
    ProjectLike,
    Question,
    QuizAttempt,
    StoredFile,
    StudentClassEnrollment,
    StudentNotification,
    TaskCompletion,
    User,
)
from app.services.audit_service import create_audit_log
from app.services.file_service import _has_active_file_reference, _has_any_file_reference
from app.services.history_snapshot_service import capture_snapshot
from app.services.soft_delete_policy import RESOURCE_POLICIES, retention_deadline
from app.services.soft_delete_service import RESOURCE_MODELS


SYSTEM_USER_ID = "system"
SYSTEM_USER_ROLE = "system"


def _to_beijing(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BEIJING_TZ)


def _as_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _is_cleanup_window(now_beijing: datetime) -> bool:
    """仅在北京时间周日且不早于 03:00 执行。"""
    return now_beijing.weekday() == 6 and (now_beijing.hour, now_beijing.minute, now_beijing.second) >= (3, 0, 0)


def _next_sunday_retry(now_beijing: datetime) -> str:
    days_ahead = (6 - now_beijing.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    retry_at = (now_beijing + timedelta(days=days_ahead)).replace(hour=3, minute=0, second=0, microsecond=0)
    return retry_at.isoformat()


def collect_file_references(db: Session, file_id: int) -> dict[str, bool]:
    """汇总文件引用状态，供清理前判断是否可删对象存储。"""
    has_snapshot = False
    for row in db.query(HistorySnapshot).filter(HistorySnapshot.fact_type == "文件引用").all():
        payload = row.payload or {}
        if payload.get("文件ID") == file_id or payload.get("封面文件ID") == file_id:
            has_snapshot = True
            break
    return {
        "has_any": _has_any_file_reference(db, file_id),
        "has_active": _has_active_file_reference(db, file_id),
        "has_snapshot": has_snapshot,
    }


def _delete_file_if_unreferenced(db: Session, file_id: int | None) -> str:
    """业务行删除后，仅当不再被任何业务记录引用时删除文件。

    历史快照已保存中文文件元数据；物理文件删除以“无业务引用”为准，
    避免本批次刚写入的文件引用快照把自己卡住。
    """
    if not file_id:
        return "无文件"
    stored = db.query(StoredFile).filter(StoredFile.id == file_id).first()
    if not stored:
        return "文件记录不存在"

    refs = collect_file_references(db, file_id)
    if refs["has_active"] or refs["has_any"]:
        return "仍有引用，跳过文件删除"

    from app.services import file_service

    adapter = getattr(file_service, "_local_adapter", None)
    if adapter is None:
        from app.core.config import settings
        from app.services.storage_local import LocalStorageAdapter

        adapter = LocalStorageAdapter(settings.local_upload_dir)
    try:
        adapter.delete(object_key=stored.object_key)
    except FileNotFoundError:
        pass
    db.delete(stored)
    db.flush()
    return "已删除文件"


def _snapshot(
    db: Session,
    *,
    resource_type: str,
    resource_id: Any,
    fact_type: str,
    fact_id: Any,
    payload: dict[str, Any],
    cleanup_batch_id: str,
) -> None:
    capture_snapshot(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        fact_type=fact_type,
        fact_id=fact_id,
        snapshot_kind=fact_type,
        payload=payload,
        cleanup_batch_id=cleanup_batch_id,
    )


def _user_name(db: Session, user_id: str | None) -> str:
    if not user_id:
        return ""
    user = db.query(User).filter(User.id == user_id).first()
    return user.name if user else str(user_id)


def _snapshot_announcement_facts(
    db: Session,
    *,
    resource_type: str,
    resource_id: Any,
    announcement: Announcement,
    cleanup_batch_id: str,
) -> int:
    count = 0
    question_ids = list(announcement.question_ids or []) if isinstance(announcement.question_ids, list) else []
    _snapshot(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        fact_type="作业摘要",
        fact_id=f"announcement-meta-{announcement.id}",
        payload={
            "作业ID": announcement.id,
            "作业标题": announcement.title,
            "教师ID": announcement.teacher_id,
            "课程ID": announcement.course_id,
            "题目IDs": question_ids,
            "题目数量": len(question_ids),
            "作业类型": announcement.type,
        },
        cleanup_batch_id=cleanup_batch_id,
    )
    count += 1
    for link in db.query(AnnouncementClass).filter(AnnouncementClass.announcement_id == announcement.id).all():
        class_name = ""
        class_row = db.query(Class).filter(Class.id == link.class_id).first()
        if class_row:
            class_name = class_row.name or ""
        _snapshot(
            db,
            resource_type=resource_type,
            resource_id=resource_id,
            fact_type="作业班级关联",
            fact_id=link.id,
            payload={
                "作业ID": announcement.id,
                "作业标题": announcement.title,
                "教师ID": announcement.teacher_id,
                "课程ID": announcement.course_id,
                "班级ID": link.class_id,
                "班级名称": class_name,
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        count += 1
    for read in db.query(AnnouncementRead).filter(AnnouncementRead.announcement_id == announcement.id).all():
        _snapshot(
            db,
            resource_type=resource_type,
            resource_id=resource_id,
            fact_type="作业已读",
            fact_id=read.id,
            payload={
                "作业ID": announcement.id,
                "作业标题": announcement.title,
                "教师ID": announcement.teacher_id,
                "课程ID": announcement.course_id,
                "用户ID": read.user_id,
                "学生姓名": _user_name(db, read.user_id),
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        count += 1
    for completion in db.query(TaskCompletion).filter(TaskCompletion.announcement_id == announcement.id).all():
        _snapshot(
            db,
            resource_type=resource_type,
            resource_id=resource_id,
            fact_type="作业完成",
            fact_id=completion.id,
            payload={
                "作业ID": announcement.id,
                "作业标题": announcement.title,
                "教师ID": announcement.teacher_id,
                "课程ID": announcement.course_id,
                "用户ID": completion.user_id,
                "学生姓名": _user_name(db, completion.user_id),
                "得分": completion.score,
                "满分": completion.max_score,
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        count += 1
    for attempt in db.query(QuizAttempt).filter(QuizAttempt.announcement_id == announcement.id).all():
        _snapshot(
            db,
            resource_type=resource_type,
            resource_id=resource_id,
            fact_type="答题记录",
            fact_id=attempt.id,
            payload={
                "作业ID": announcement.id,
                "作业标题": announcement.title,
                "教师ID": announcement.teacher_id,
                "课程ID": announcement.course_id,
                "题目ID": attempt.question_id,
                "用户ID": attempt.user_id,
                "学生姓名": _user_name(db, attempt.user_id),
                "作答": attempt.user_answer,
                "是否正确": bool(attempt.is_correct),
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        count += 1
    return count


def _delete_announcement_facts(db: Session, announcement_id: int) -> None:
    db.query(QuizAttempt).filter(QuizAttempt.announcement_id == announcement_id).delete(synchronize_session=False)
    db.query(TaskCompletion).filter(TaskCompletion.announcement_id == announcement_id).delete(synchronize_session=False)
    db.query(AnnouncementRead).filter(AnnouncementRead.announcement_id == announcement_id).delete(synchronize_session=False)
    db.query(AnnouncementClass).filter(AnnouncementClass.announcement_id == announcement_id).delete(synchronize_session=False)


def _cleanup_material(db: Session, material: Material, cleanup_batch_id: str) -> dict[str, Any]:
    snapshot_count = 0
    file_result = "无文件"
    preview = db.query(MaterialPreview).filter(MaterialPreview.material_id == material.id).first()
    if preview:
        _snapshot(
            db,
            resource_type="materials",
            resource_id=material.id,
            fact_type="资料预览",
            fact_id=preview.id,
            payload={
                "资料ID": material.id,
                "资料标题": material.title,
                "预览状态": preview.status,
                "封面文件ID": preview.cover_file_id,
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1
    if material.file_id:
        _snapshot(
            db,
            resource_type="materials",
            resource_id=material.id,
            fact_type="文件引用",
            fact_id=f"material-file-{material.id}",
            payload={"资料ID": material.id, "资料标题": material.title, "文件ID": material.file_id},
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1

    file_id = material.file_id
    cover_file_id = preview.cover_file_id if preview else None
    if preview:
        db.delete(preview)
    db.delete(material)
    db.flush()
    file_result = _delete_file_if_unreferenced(db, file_id)
    if cover_file_id and cover_file_id != file_id:
        cover_result = _delete_file_if_unreferenced(db, cover_file_id)
        file_result = f"{file_result}; 封面:{cover_result}"
    return {"历史快照数量": snapshot_count, "文件处理结果": file_result}


def _cleanup_project(db: Session, project: Project, cleanup_batch_id: str) -> dict[str, Any]:
    snapshot_count = 0
    _snapshot(
        db,
        resource_type="projects",
        resource_id=project.id,
        fact_type="作品摘要",
        fact_id=f"project-meta-{project.id}",
        payload={
            "作品ID": project.id,
            "作品标题": project.title,
            "作者ID": project.author_id,
            "作者姓名": _user_name(db, project.author_id),
            "课程ID": project.course_id,
            "专业": project.major or "",
            "描述": project.description or "",
            "标签": list(project.tags or []) if isinstance(project.tags, list) else [],
            "点赞数": int(project.likes or 0),
            "是否精选": bool(project.featured),
            "状态": project.status or "",
            "日期": project.date or "",
            # 清理后不再保留可跳转详情地址
            "视频地址": "",
            "报告地址": "",
            "封面地址": "",
        },
        cleanup_batch_id=cleanup_batch_id,
    )
    snapshot_count += 1
    for image in db.query(ProjectImage).filter(ProjectImage.project_id == project.id).all():
        _snapshot(
            db,
            resource_type="projects",
            resource_id=project.id,
            fact_type="作品图片",
            fact_id=image.id,
            payload={
                "作品ID": project.id,
                "作品标题": project.title,
                "图片地址": "",
                "文件ID": image.file_id,
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1
    for like in db.query(ProjectLike).filter(ProjectLike.project_id == project.id).all():
        _snapshot(
            db,
            resource_type="projects",
            resource_id=project.id,
            fact_type="作品点赞",
            fact_id=like.id,
            payload={
                "作品ID": project.id,
                "作品标题": project.title,
                "用户ID": like.user_id,
                "学生姓名": _user_name(db, like.user_id),
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1
    for file_id, label in ((project.report_file_id, "报告文件"), (project.cover_file_id, "封面文件")):
        if file_id:
            _snapshot(
                db,
                resource_type="projects",
                resource_id=project.id,
                fact_type="文件引用",
                fact_id=f"project-{label}-{project.id}",
                payload={"作品ID": project.id, "作品标题": project.title, "文件ID": file_id, "文件类型": label},
                cleanup_batch_id=cleanup_batch_id,
            )
            snapshot_count += 1

    image_file_ids = [
        image.file_id
        for image in db.query(ProjectImage).filter(ProjectImage.project_id == project.id).all()
        if image.file_id
    ]
    report_file_id = project.report_file_id
    cover_file_id = project.cover_file_id
    db.query(ProjectLike).filter(ProjectLike.project_id == project.id).delete(synchronize_session=False)
    db.query(ProjectImage).filter(ProjectImage.project_id == project.id).delete(synchronize_session=False)
    db.query(StudentNotification).filter(StudentNotification.project_id == project.id).delete(synchronize_session=False)
    db.delete(project)
    db.flush()

    results = []
    for file_id in {report_file_id, cover_file_id, *image_file_ids}:
        if file_id:
            results.append(_delete_file_if_unreferenced(db, file_id))
    return {
        "历史快照数量": snapshot_count,
        "文件处理结果": "；".join(results) if results else "无文件",
    }


def _cleanup_question(db: Session, question: Question, cleanup_batch_id: str) -> dict[str, Any]:
    snapshot_count = 0
    for attempt in db.query(QuizAttempt).filter(QuizAttempt.question_id == question.id).all():
        _snapshot(
            db,
            resource_type="questions",
            resource_id=question.id,
            fact_type="答题记录",
            fact_id=attempt.id,
            payload={
                "题目ID": question.id,
                "题干": question.stem,
                "用户ID": attempt.user_id,
                "学生姓名": _user_name(db, attempt.user_id),
                "作业ID": attempt.announcement_id,
                "作答": attempt.user_answer,
                "是否正确": bool(attempt.is_correct),
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1
    for ann in db.query(Announcement).filter(Announcement.question_ids.isnot(None)).all():
        ids = list(ann.question_ids or [])
        if question.id in ids:
            _snapshot(
                db,
                resource_type="questions",
                resource_id=question.id,
                fact_type="作业题目上下文",
                fact_id=f"announcement-{ann.id}-question-{question.id}",
                payload={
                    "题目ID": question.id,
                    "题干": question.stem,
                    "作业ID": ann.id,
                    "作业标题": ann.title,
                },
                cleanup_batch_id=cleanup_batch_id,
            )
            snapshot_count += 1

    db.query(QuizAttempt).filter(QuizAttempt.question_id == question.id).delete(synchronize_session=False)
    db.delete(question)
    db.flush()
    return {"历史快照数量": snapshot_count, "文件处理结果": "无文件"}


def _cleanup_announcement(db: Session, announcement: Announcement, cleanup_batch_id: str) -> dict[str, Any]:
    snapshot_count = _snapshot_announcement_facts(
        db,
        resource_type="announcements",
        resource_id=announcement.id,
        announcement=announcement,
        cleanup_batch_id=cleanup_batch_id,
    )
    _delete_announcement_facts(db, announcement.id)
    db.delete(announcement)
    db.flush()
    return {"历史快照数量": snapshot_count, "文件处理结果": "无文件"}


def _cleanup_class(db: Session, cls: Class, cleanup_batch_id: str) -> dict[str, Any]:
    snapshot_count = 0
    for enrollment in db.query(StudentClassEnrollment).filter(StudentClassEnrollment.class_id == cls.id).all():
        _snapshot(
            db,
            resource_type="classes",
            resource_id=cls.id,
            fact_type="班级选课",
            fact_id=enrollment.id,
            payload={
                "班级ID": cls.id,
                "班级名称": cls.name,
                "用户ID": enrollment.user_id,
                "学生姓名": _user_name(db, enrollment.user_id),
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1
    for link in db.query(AnnouncementClass).filter(AnnouncementClass.class_id == cls.id).all():
        _snapshot(
            db,
            resource_type="classes",
            resource_id=cls.id,
            fact_type="作业班级关联",
            fact_id=link.id,
            payload={"班级ID": cls.id, "班级名称": cls.name, "作业ID": link.announcement_id},
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1

    db.query(AnnouncementClass).filter(AnnouncementClass.class_id == cls.id).delete(synchronize_session=False)
    db.query(StudentClassEnrollment).filter(StudentClassEnrollment.class_id == cls.id).delete(synchronize_session=False)
    db.delete(cls)
    db.flush()
    return {"历史快照数量": snapshot_count, "文件处理结果": "无文件"}


def _cleanup_user(db: Session, user: User, cleanup_batch_id: str) -> dict[str, Any]:
    snapshot_count = 0
    for project in db.query(Project).filter(Project.author_id == user.id).all():
        _snapshot(
            db,
            resource_type="users",
            resource_id=user.id,
            fact_type="用户作品",
            fact_id=project.id,
            payload={
                "用户ID": user.id,
                "用户姓名": user.name,
                "作品ID": project.id,
                "作品标题": project.title,
                "作者ID": user.id,
                "作者姓名": user.name,
                "课程ID": project.course_id,
                "专业": project.major or "",
                "描述": project.description or "",
                "标签": list(project.tags or []) if isinstance(project.tags, list) else [],
                "点赞数": int(project.likes or 0),
                "是否精选": bool(project.featured),
                "状态": project.status or "",
                "日期": project.date or "",
                "视频地址": "",
                "报告地址": "",
                "封面地址": "",
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1
    for attempt in db.query(QuizAttempt).filter(QuizAttempt.user_id == user.id).all():
        _snapshot(
            db,
            resource_type="users",
            resource_id=user.id,
            fact_type="答题记录",
            fact_id=attempt.id,
            payload={
                "用户ID": user.id,
                "用户姓名": user.name,
                "题目ID": attempt.question_id,
                "作业ID": attempt.announcement_id,
                "作答": attempt.user_answer,
                "是否正确": bool(attempt.is_correct),
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1
    for enrollment in db.query(StudentClassEnrollment).filter(StudentClassEnrollment.user_id == user.id).all():
        _snapshot(
            db,
            resource_type="users",
            resource_id=user.id,
            fact_type="班级关系",
            fact_id=enrollment.id,
            payload={
                "用户ID": user.id,
                "用户姓名": user.name,
                "班级ID": enrollment.class_id,
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1
    for like in db.query(ProjectLike).filter(ProjectLike.user_id == user.id).all():
        _snapshot(
            db,
            resource_type="users",
            resource_id=user.id,
            fact_type="作品点赞",
            fact_id=like.id,
            payload={"用户ID": user.id, "用户姓名": user.name, "作品ID": like.project_id},
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1
    for notice in db.query(StudentNotification).filter(StudentNotification.user_id == user.id).all():
        _snapshot(
            db,
            resource_type="users",
            resource_id=user.id,
            fact_type="通知",
            fact_id=notice.id,
            payload={
                "用户ID": user.id,
                "用户姓名": user.name,
                "通知标题": notice.title,
                "通知类型": notice.type,
            },
            cleanup_batch_id=cleanup_batch_id,
        )
        snapshot_count += 1

    # 用户清理不物理删除作品本体（作品按自身保留期处理），只清理直接依赖用户的事实。
    db.query(QuizAttempt).filter(QuizAttempt.user_id == user.id).delete(synchronize_session=False)
    db.query(StudentClassEnrollment).filter(StudentClassEnrollment.user_id == user.id).delete(synchronize_session=False)
    db.query(ProjectLike).filter(ProjectLike.user_id == user.id).delete(synchronize_session=False)
    db.query(StudentNotification).filter(StudentNotification.user_id == user.id).delete(synchronize_session=False)
    db.query(AnnouncementRead).filter(AnnouncementRead.user_id == user.id).delete(synchronize_session=False)
    db.query(TaskCompletion).filter(TaskCompletion.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.flush()
    return {"历史快照数量": snapshot_count, "文件处理结果": "无文件"}


def _cleanup_course(db: Session, course: Course, cleanup_batch_id: str) -> dict[str, Any]:
    snapshot_count = 0
    file_results: list[str] = []
    same_batch = {
        "deleted_at": course.deleted_at,
        "deleted_by": course.deleted_by,
    }

    classes = db.query(Class).filter(
        Class.course_id == course.id,
        Class.deleted_at == same_batch["deleted_at"],
        Class.deleted_by == same_batch["deleted_by"],
    ).all()
    materials = db.query(Material).filter(
        Material.course_id == course.id,
        Material.deleted_at == same_batch["deleted_at"],
        Material.deleted_by == same_batch["deleted_by"],
    ).all()
    announcements = db.query(Announcement).filter(
        Announcement.course_id == course.id,
        Announcement.deleted_at == same_batch["deleted_at"],
        Announcement.deleted_by == same_batch["deleted_by"],
    ).all()

    for cls in classes:
        result = _cleanup_class(db, cls, cleanup_batch_id)
        snapshot_count += result["历史快照数量"]
    for material in materials:
        result = _cleanup_material(db, material, cleanup_batch_id)
        snapshot_count += result["历史快照数量"]
        file_results.append(str(result["文件处理结果"]))
    for announcement in announcements:
        result = _cleanup_announcement(db, announcement, cleanup_batch_id)
        snapshot_count += result["历史快照数量"]

    # 使用 Core DELETE，避免 ORM relationship cascade 误删“单独软删、尚未到期”的子资源。
    db.execute(delete(Course).where(Course.id == course.id))
    db.flush()
    return {
        "历史快照数量": snapshot_count,
        "文件处理结果": "；".join(file_results) if file_results else "无文件",
    }


_CLEANERS = {
    "courses": _cleanup_course,
    "classes": _cleanup_class,
    "announcements": _cleanup_announcement,
    "materials": _cleanup_material,
    "projects": _cleanup_project,
    "questions": _cleanup_question,
    "users": _cleanup_user,
}


def _iter_expired_resources(db: Session, resource_type: str, now_beijing: datetime):
    model = RESOURCE_MODELS[resource_type]
    rows = db.query(model).filter(model.deleted_at.isnot(None)).all()
    for row in rows:
        deadline = retention_deadline(row.deleted_at, resource_type)
        if deadline <= now_beijing:
            yield row, deadline


def _cleanup_one(
    db: Session,
    *,
    resource_type: str,
    row: Any,
    deadline: datetime,
    now_beijing: datetime,
) -> None:
    cleanup_batch_id = str(uuid.uuid4())
    cleaner = _CLEANERS[resource_type]
    result = cleaner(db, row, cleanup_batch_id)
    create_audit_log(
        db,
        user_id=SYSTEM_USER_ID,
        user_role=SYSTEM_USER_ROLE,
        action="system.soft_delete_cleanup",
        resource_type=resource_type,
        resource_id=getattr(row, "id", None),
        resource_name=str(getattr(row, "name", None) or getattr(row, "title", None) or getattr(row, "stem", None) or getattr(row, "id", "")),
        details={
            "清理结果": "系统自动清理成功",
            "到期时间": deadline.isoformat(),
            "历史快照数量": result.get("历史快照数量", 0),
            "文件处理结果": result.get("文件处理结果", "无文件"),
            "清理批次": cleanup_batch_id,
            "资源类型名称": RESOURCE_POLICIES[resource_type].display_name,
        },
        status="success",
    )
    db.commit()


def cleanup_expired_resources(db: Session, now: datetime | None = None) -> dict[str, int]:
    """按固定策略执行到期快照与物理清理。

    - 仅北京时间周日 03:00 及之后执行
    - 每个资源独立事务，失败只回滚当前资源
    """
    now_beijing = _to_beijing(now)
    if not _is_cleanup_window(now_beijing):
        return {"cleaned_count": 0, "failed_count": 0}

    cleaned_count = 0
    failed_count = 0

    # 先清理题目（保留答题快照），再清理作业/资料等，最后课程与用户。
    resource_order = (
        "questions",
        "announcements",
        "materials",
        "projects",
        "classes",
        "courses",
        "users",
    )
    for resource_type in resource_order:
        for row, deadline in list(_iter_expired_resources(db, resource_type, now_beijing)):
            try:
                # 重新取一次，避免前面清理后对象过期
                model = RESOURCE_MODELS[resource_type]
                current = db.query(model).filter(model.id == row.id, model.deleted_at.isnot(None)).first()
                if not current:
                    continue
                _cleanup_one(
                    db,
                    resource_type=resource_type,
                    row=current,
                    deadline=deadline,
                    now_beijing=now_beijing,
                )
                cleaned_count += 1
            except Exception as exc:  # noqa: BLE001 - 清理任务需要吞掉单项失败并审计
                db.rollback()
                failed_count += 1
                create_audit_log(
                    db,
                    user_id=SYSTEM_USER_ID,
                    user_role=SYSTEM_USER_ROLE,
                    action="system.soft_delete_cleanup",
                    resource_type=resource_type,
                    resource_id=getattr(row, "id", None),
                    resource_name=str(getattr(row, "name", None) or getattr(row, "title", None) or getattr(row, "stem", None) or getattr(row, "id", "")),
                    details={
                        "清理结果": "系统自动清理失败",
                        "失败原因": str(exc),
                        "下次重试时间": _next_sunday_retry(now_beijing),
                        "资源类型名称": RESOURCE_POLICIES[resource_type].display_name,
                    },
                    status="failed",
                    error_message=str(exc),
                )
                db.commit()

    return {"cleaned_count": cleaned_count, "failed_count": failed_count}
