"""题目任务完成服务。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import (
    Announcement,
    AnnouncementClass,
    Class,
    Course,
    QuizAttempt,
    StudentClassEnrollment,
    TaskCompletion,
    User,
)
from app.services.history_snapshot_service import (
    history_attempt_totals,
    history_completion_rows,
    history_task_catalog,
)


# 北京时间时区偏移（UTC+8）
BEIJING_TIME_DELTA = timedelta(hours=8)
BEIJING_TZ = timezone(BEIJING_TIME_DELTA)


def _get_now_beijing() -> datetime:
    """获取当前北京时间（带时区信息）"""
    return datetime.now(BEIJING_TZ)


def _to_beijing_time(dt: datetime) -> datetime:
    """将时间转换为北京时间（确保带时区信息）"""
    if dt.tzinfo is None:
        # 数据库存储的 naive 时间按 UTC 处理，再转换为北京时间。
        return dt.replace(tzinfo=timezone.utc).astimezone(BEIJING_TZ)
    # 如果有时区信息，转换为北京时间
    return dt.astimezone(BEIJING_TZ)


def _student_can_access(db: Session, user_id: str, announcement_id: int) -> bool:
    """学生可访问任务：作业本身、目标班级、所属课程均未软删。"""
    class_ids = [
        row.class_id
        for row in (
            db.query(StudentClassEnrollment.class_id)
            .join(Class, Class.id == StudentClassEnrollment.class_id)
            .join(Course, Course.id == Class.course_id)
            .filter(
                StudentClassEnrollment.user_id == user_id,
                Class.deleted_at.is_(None),
                Course.deleted_at.is_(None),
            )
            .all()
        )
    ]
    if not class_ids:
        return False
    return (
        db.query(AnnouncementClass)
        .join(Announcement, Announcement.id == AnnouncementClass.announcement_id)
        .join(Class, Class.id == AnnouncementClass.class_id)
        .join(Course, Course.id == Class.course_id)
        .filter(
            AnnouncementClass.announcement_id == announcement_id,
            AnnouncementClass.class_id.in_(class_ids),
            Announcement.deleted_at.is_(None),
            Class.deleted_at.is_(None),
            Course.deleted_at.is_(None),
        )
        .first()
        is not None
    )


def _is_not_started(ann: Announcement) -> bool:
    """判断任务是否尚未开始。"""
    return bool(ann.start_time and _get_now_beijing() < _to_beijing_time(ann.start_time))


def _is_expired(end_time: datetime | None) -> bool:
    """判断任务是否已过期（使用北京时间）"""
    if not end_time:
        return False
    return _get_now_beijing() > _to_beijing_time(end_time)


def validate_assignment_available(ann: Announcement) -> None:
    """校验任务是否处于可答题/可完成时间窗口。"""
    if _is_not_started(ann):
        raise BusinessException(400, "该任务尚未开始")
    if _is_expired(ann.end_time):
        raise BusinessException(400, "该任务已截止，无法继续操作")


def get_accessible_assignment(db: Session, user_id: str, announcement_id: int) -> Announcement | None:
    """获取学生可访问的任务（排除已软删作业）。"""
    ann = db.query(Announcement).filter(
        Announcement.id == announcement_id,
        Announcement.deleted_at.is_(None),
    ).first()
    if not ann or not _student_can_access(db, user_id, announcement_id):
        return None
    return ann


def get_assignment_questions(db: Session, user_id: str, announcement_id: int) -> tuple[Announcement, list]:
    """获取学生任务题目，并统一校验权限和时间窗口。"""
    from app.models.entities import Question

    ann = get_accessible_assignment(db, user_id, announcement_id)
    if not ann:
        raise BusinessException(404, "题目任务不存在")
    validate_assignment_available(ann)

    question_ids = ann.question_ids if isinstance(ann.question_ids, list) else []
    if not question_ids:
        raise BusinessException(400, "该任务暂无题目")

    # 作业题目也排除软删题，避免把已删除题继续下发给学生。
    questions = db.query(Question).filter(
        Question.id.in_(question_ids),
        Question.deleted_at.is_(None),
    ).order_by(Question.id).all()
    question_by_id = {question.id: question for question in questions}
    ordered_questions = [question_by_id[qid] for qid in question_ids if qid in question_by_id]
    if len(ordered_questions) != len(set(question_ids)):
        raise BusinessException(400, "该任务题目配置异常")
    return ann, ordered_questions


def _answered_question_ids_for_assignment(db: Session, user_id: str, announcement_id: int) -> set[int]:
    """获取学生在指定任务下已答题目 ID。"""
    return {
        row.question_id for row in db.query(QuizAttempt.question_id)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.announcement_id == announcement_id,
        )
        .distinct()
        .all()
    }


def mark_completed(db: Session, user_id: str, announcement_id: int):
    ann = get_accessible_assignment(db, user_id, announcement_id)
    if not ann:
        return None
    validate_assignment_available(ann)
    existing = db.query(TaskCompletion).filter(
        TaskCompletion.user_id == user_id,
        TaskCompletion.announcement_id == announcement_id,
    ).first()

    question_ids = set(ann.question_ids if isinstance(ann.question_ids, list) else [])
    if question_ids:
        answered_ids = _answered_question_ids_for_assignment(db, user_id, announcement_id)
        if not question_ids.issubset(answered_ids):
            raise BusinessException(400, "请先完成全部题目后再标记完成")
    if existing:
        return existing

    try:
        completion = TaskCompletion(user_id=user_id, announcement_id=announcement_id)
        db.add(completion)
        db.commit()
        db.refresh(completion)
        return completion
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "标记完成失败")


def completion_report(
    db: Session,
    announcement_id: int,
    teacher_id: str,
    class_id: int | None = None,
    completed_page: int = 1,
    completed_page_size: int = 20,
    incomplete_page: int = 1,
    incomplete_page_size: int = 20,
):
    ann = db.query(Announcement).filter(
        Announcement.id == announcement_id,
        Announcement.teacher_id == teacher_id,
    ).first()

    # 活跃作业走原路径；已清理作业回退历史快照
    if ann is None:
        return _completion_report_from_history(
            db,
            announcement_id=announcement_id,
            teacher_id=teacher_id,
            class_id=class_id,
            completed_page=completed_page,
            completed_page_size=completed_page_size,
            incomplete_page=incomplete_page,
            incomplete_page_size=incomplete_page_size,
        )

    class_links = db.query(AnnouncementClass).filter(AnnouncementClass.announcement_id == announcement_id).all()
    if class_id is not None:
        class_links = [link for link in class_links if link.class_id == class_id]
    class_ids = [link.class_id for link in class_links]
    students = (
        db.query(User, StudentClassEnrollment.class_id)
        .join(StudentClassEnrollment, StudentClassEnrollment.user_id == User.id)
        .filter(
            StudentClassEnrollment.class_id.in_(class_ids),
            User.role == "student",
            User.deleted_at.is_(None),
        )
        .all()
    )
    completed_ids = {
        row.user_id for row in db.query(TaskCompletion.user_id)
        .filter(TaskCompletion.announcement_id == announcement_id)
        .all()
    }

    class_name_by_id = {
        link.class_id: link.class_.name if link.class_ else ""
        for link in class_links
    }
    seen_student_ids: set[str] = set()
    completed_students = []
    incomplete_students = []
    per_class = []

    # 计算成绩：获取此任务的题目列表和每个学生的答题情况
    question_ids = ann.question_ids if isinstance(ann.question_ids, list) else []
    total_questions = len(question_ids)

    # 预计算每个学生在此任务中的成绩：按任务上下文、每题最新一次答题结果统计。
    student_scores: dict[str, int] = {}
    if question_ids:
        latest_attempt_ids = (
            db.query(func.max(QuizAttempt.id).label("attempt_id"))
            .filter(
                QuizAttempt.announcement_id == announcement_id,
                QuizAttempt.question_id.in_(question_ids),
            )
            .group_by(QuizAttempt.user_id, QuizAttempt.question_id)
            .subquery()
        )
        attempts = (
            db.query(QuizAttempt.user_id, QuizAttempt.question_id, QuizAttempt.is_correct)
            .join(latest_attempt_ids, QuizAttempt.id == latest_attempt_ids.c.attempt_id)
            .all()
        )
        score_counts: dict[str, int] = {}
        for user_id, question_id, is_correct in attempts:
            if is_correct:
                score_counts[user_id] = score_counts.get(user_id, 0) + 1
        for user_id, correct_count in score_counts.items():
            student_scores[user_id] = min(100, round(correct_count / total_questions * 100)) if total_questions > 0 else 0

    # 历史快照补充（作业仍在但部分学生/完成已被清理）
    history_scores = history_attempt_totals(
        db, announcement_ids=[announcement_id]
    ).get("task_scores", {})
    for (user_id, task_id), score in history_scores.items():
        if task_id == announcement_id:
            student_scores.setdefault(user_id, score)
    for row in history_completion_rows(
        db, announcement_ids=[announcement_id], teacher_id=teacher_id
    ):
        completed_ids.add(row["user_id"])
        if row.get("score") is not None:
            student_scores.setdefault(row["user_id"], int(row["score"]))

    for current_class_id in class_ids:
        # 修复：原循环变量 class_id 与函数参数同名，导致函数参数被遮蔽，改用 current_class_id
        class_students = [(student, cid) for student, cid in students if cid == current_class_id]
        class_completed = 0
        for student, _ in class_students:
            payload = {
                "id": student.id,
                "name": student.name,
                "major": student.major,
                "class_id": current_class_id,
                "class_name": class_name_by_id.get(current_class_id, ""),
                "score": student_scores.get(student.id, 0),
                "total_questions": total_questions,
            }
            if student.id in completed_ids:
                class_completed += 1
                if student.id not in seen_student_ids:
                    completed_students.append(payload)
            elif student.id not in seen_student_ids:
                incomplete_students.append(payload)
            seen_student_ids.add(student.id)
        per_class.append({
            "class_id": current_class_id,
            "class_name": class_name_by_id.get(current_class_id, ""),
            "total": len(class_students),
            "completed": class_completed,
        })

    # 对已完成/未完成学生列表进行分页
    completed_total = len(completed_students)
    incomplete_total = len(incomplete_students)
    completed_start = (completed_page - 1) * completed_page_size
    incomplete_start = (incomplete_page - 1) * incomplete_page_size

    return {
        "announcement_id": ann.id,
        "announcement_title": ann.title,
        "course_id": ann.course_id,
        "class_names": [class_name_by_id.get(class_id, "") for class_id in class_ids],
        "total_students": len(seen_student_ids),
        "completed_students": {
            "items": completed_students[completed_start:completed_start + completed_page_size],
            "total": completed_total,
            "page": completed_page,
            "page_size": completed_page_size,
        },
        "completed_count": completed_total,
        "incomplete_students": {
            "items": incomplete_students[incomplete_start:incomplete_start + incomplete_page_size],
            "total": incomplete_total,
            "page": incomplete_page,
            "page_size": incomplete_page_size,
        },
        "per_class": per_class,
        "is_expired": _is_expired(ann.end_time),
        "deadline": _iso(ann.end_time),
        "created_at": _iso(ann.created_at),
        "total_questions": total_questions,
        "source": "live",
    }


def _completion_report_from_history(
    db: Session,
    *,
    announcement_id: int,
    teacher_id: str,
    class_id: int | None,
    completed_page: int,
    completed_page_size: int,
    incomplete_page: int,
    incomplete_page_size: int,
) -> dict | None:
    """作业本体已清理时，仅基于历史快照生成完成报告。"""
    catalog = {
        item["announcement_id"]: item
        for item in history_task_catalog(db, teacher_id=teacher_id, announcement_ids=[announcement_id])
    }
    task = catalog.get(announcement_id)
    completions = history_completion_rows(
        db,
        announcement_ids=[announcement_id],
        teacher_id=teacher_id,
    )
    if task is None and not completions:
        return None

    title = task["title"] if task else (
        completions[0]["announcement_title"] if completions else f"历史作业#{announcement_id}"
    )
    course_id = task.get("course_id") if task else (
        completions[0].get("course_id") if completions else None
    )
    total_questions = task.get("total_questions", 0) if task else (
        completions[0].get("total_questions", 0) if completions else 0
    )
    class_ids = list(task.get("class_ids") or []) if task else []
    class_name_by_id = {}
    if task:
        for idx, cid in enumerate(class_ids):
            names = task.get("class_names") or []
            class_name_by_id[cid] = names[idx] if idx < len(names) else ""
    if class_id is not None:
        class_ids = [cid for cid in class_ids if cid == class_id]

    history_scores = history_attempt_totals(
        db, announcement_ids=[announcement_id]
    ).get("task_scores", {})

    completed_students = []
    seen: set[str] = set()
    for row in completions:
        user_id = row["user_id"]
        if user_id in seen:
            continue
        seen.add(user_id)
        score = row.get("score")
        if score is None:
            score = history_scores.get((user_id, announcement_id), 0)
        student_class_ids = row.get("class_ids") or class_ids
        if class_id is not None and student_class_ids and class_id not in student_class_ids:
            continue
        current_class_id = class_id if class_id is not None else (
            student_class_ids[0] if student_class_ids else None
        )
        completed_students.append({
            "id": user_id,
            "name": row.get("student_name") or user_id,
            "major": "",
            "class_id": current_class_id,
            "class_name": class_name_by_id.get(current_class_id, "") if current_class_id else "",
            "score": int(score or 0),
            "total_questions": total_questions or row.get("total_questions") or 0,
        })

    completed_total = len(completed_students)
    completed_start = (completed_page - 1) * completed_page_size
    incomplete_start = (incomplete_page - 1) * incomplete_page_size
    per_class = []
    for cid in class_ids:
        count = sum(1 for item in completed_students if item.get("class_id") == cid)
        per_class.append({
            "class_id": cid,
            "class_name": class_name_by_id.get(cid, ""),
            "total": count,
            "completed": count,
        })

    return {
        "announcement_id": announcement_id,
        "announcement_title": title,
        "course_id": course_id,
        "class_names": [class_name_by_id.get(cid, "") for cid in class_ids],
        "total_students": completed_total,
        "completed_students": {
            "items": completed_students[completed_start:completed_start + completed_page_size],
            "total": completed_total,
            "page": completed_page,
            "page_size": completed_page_size,
        },
        "completed_count": completed_total,
        "incomplete_students": {
            "items": [],
            "total": 0,
            "page": incomplete_page,
            "page_size": incomplete_page_size,
        },
        "per_class": per_class,
        "is_expired": True,
        "deadline": "",
        "created_at": "",
        "total_questions": total_questions,
        "source": "history_snapshot",
        # 清理后不返回详情跳转
        "detail_url": "",
    }


def _iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def task_overview(db: Session, teacher_id: str, course_id: int | None = None) -> dict:
    """教师所有任务的总览：总完成数、未完成数，以及每个任务的简要信息。"""
    query = db.query(Announcement).filter(
        Announcement.teacher_id == teacher_id,
        Announcement.type == "quiz",
    )
    if course_id is not None:
        query = query.filter(Announcement.course_id == course_id)
    anns = query.order_by(Announcement.created_at.desc()).all()
    if not anns:
        return {"total_tasks": 0, "total_completed": 0, "total_incomplete": 0, "tasks": []}

    ann_ids = [ann.id for ann in anns]

    # 每个任务的班级信息
    class_links = db.query(AnnouncementClass).filter(AnnouncementClass.announcement_id.in_(ann_ids)).all()
    ann_class_ids: dict[int, list[int]] = {}
    class_id_set: set[int] = set()
    for link in class_links:
        ann_class_ids.setdefault(link.announcement_id, []).append(link.class_id)
        class_id_set.add(link.class_id)

    # 班级名称映射
    from app.models.entities import Class
    class_names_map = {c.id: c.name for c in db.query(Class).filter(Class.id.in_(class_id_set)).all()} if class_id_set else {}

    # 每个任务的已完成人数
    completion_counts = dict(
        db.query(TaskCompletion.announcement_id, func.count(TaskCompletion.user_id))
        .filter(TaskCompletion.announcement_id.in_(ann_ids))
        .group_by(TaskCompletion.announcement_id)
        .all()
    )

    # 每个任务关联的去重学生数（按任务+班级统计学生，再跨班级去重）
    if class_id_set:
        enrollments = (
            db.query(StudentClassEnrollment.user_id, StudentClassEnrollment.class_id)
            .filter(StudentClassEnrollment.class_id.in_(class_id_set))
            .all()
        )
    else:
        enrollments = []

    # 构建 class_id -> set of student_ids
    class_students: dict[int, set[str]] = {}
    for uid, cid in enrollments:
        class_students.setdefault(cid, set()).add(uid)

    # 按学生汇总：学生 → { 分配的任务ID集合, 完成的任务ID集合 }
    student_assigned: dict[str, set[int]] = {}
    student_completed: dict[str, set[int]] = {}
    tasks = []

    for ann in anns:
        cids = ann_class_ids.get(ann.id, [])
        # 跨班级去重学生
        student_ids: set[str] = set()
        for cid in cids:
            student_ids.update(class_students.get(cid, set()))
        total = len(student_ids)
        completed = completion_counts.get(ann.id, 0)
        # 按学生汇总：记录每个人被分配了哪些任务、完成了哪些
        completed_set = set(
            row.user_id for row in db.query(TaskCompletion.user_id)
            .filter(TaskCompletion.announcement_id == ann.id, TaskCompletion.user_id.in_(student_ids))
            .all()
        ) if student_ids else set()
        for sid in student_ids:
            student_assigned.setdefault(sid, set()).add(ann.id)
            if sid in completed_set:
                student_completed.setdefault(sid, set()).add(ann.id)
        tasks.append({
            "id": ann.id,
            "title": ann.title,
            "course_id": ann.course_id,
            "course_name": ann.course.name if ann.course else "",
            "class_names": [class_names_map.get(cid, "") for cid in cids],
            "total_students": total,
            "completed_count": completed,
            "is_expired": _is_expired(ann.end_time),
            "created_at": _iso(ann.created_at),
        })

    # 汇总：完成了所有分配任务的学生 = 已完成；至少一个未完成 = 未完成
    total_completed = 0
    total_incomplete = 0
    for sid in student_assigned:
        assigned = student_assigned.get(sid, set())
        completed_set = student_completed.get(sid, set())
        if assigned and assigned == completed_set:
            total_completed += 1
        else:
            total_incomplete += 1

    return {
        "total_tasks": len(anns),
        "total_completed": total_completed,
        "total_incomplete": total_incomplete,
        "tasks": tasks,
    }
