"""不可变历史快照的读写辅助。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.entities import HistorySnapshot


def capture_snapshot(
    db: Session,
    resource_type: str,
    resource_id: str | int,
    fact_type: str,
    fact_id: str | int,
    snapshot_kind: str,
    payload: dict[str, Any],
    cleanup_batch_id: str | None = None,
) -> HistorySnapshot:
    """插入一条快照；同一事实键已存在时返回旧行。

    本函数只 flush 不 commit，事务由调用方负责。
    """

    normalized_fact_type = str(fact_type)
    normalized_fact_id = str(fact_id)
    existing = (
        db.query(HistorySnapshot)
        .filter(
            HistorySnapshot.fact_type == normalized_fact_type,
            HistorySnapshot.fact_id == normalized_fact_id,
        )
        .first()
    )
    if existing is not None:
        return existing

    now = datetime.now(timezone.utc)
    snapshot = HistorySnapshot(
        resource_type=str(resource_type),
        resource_id=str(resource_id),
        fact_type=normalized_fact_type,
        fact_id=normalized_fact_id,
        snapshot_kind=str(snapshot_kind),
        cleanup_batch_id=str(cleanup_batch_id) if cleanup_batch_id is not None else None,
        payload=dict(payload),
        captured_at=now,
        created_at=now,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def list_snapshots(
    db: Session,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
    cleanup_batch_id: str | None = None,
    fact_type: str | None = None,
    fact_id: str | int | None = None,
) -> list[dict[str, Any]]:
    """按条件读取快照为不可变字典列表。"""

    query = db.query(HistorySnapshot)
    if resource_type is not None:
        query = query.filter(HistorySnapshot.resource_type == str(resource_type))
    if resource_id is not None:
        query = query.filter(HistorySnapshot.resource_id == str(resource_id))
    if cleanup_batch_id is not None:
        query = query.filter(HistorySnapshot.cleanup_batch_id == str(cleanup_batch_id))
    if fact_type is not None:
        query = query.filter(HistorySnapshot.fact_type == str(fact_type))
    if fact_id is not None:
        query = query.filter(HistorySnapshot.fact_id == str(fact_id))

    rows = query.order_by(HistorySnapshot.captured_at.asc(), HistorySnapshot.id.asc()).all()
    return [
        {
            "id": row.id,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "fact_type": row.fact_type,
            "fact_id": row.fact_id,
            "snapshot_kind": row.snapshot_kind,
            "cleanup_batch_id": row.cleanup_batch_id,
            "payload": dict(row.payload or {}),
            "captured_at": row.captured_at,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "是"}
    return False


def _as_score(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _payload(row: HistorySnapshot | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row.get("payload") or {})
    return dict(row.payload or {})


def _fact_key(row: HistorySnapshot | dict[str, Any]) -> tuple[str, str]:
    if isinstance(row, dict):
        batch = row.get("cleanup_batch_id") or ""
        fact_id = str(row.get("fact_id") or "")
        return str(batch), fact_id
    return str(row.cleanup_batch_id or ""), str(row.fact_id or "")


def _query_fact_rows(
    db: Session,
    fact_types: Iterable[str],
    *,
    user_ids: Iterable[str] | None = None,
) -> list[HistorySnapshot]:
    types = [str(item) for item in fact_types]
    query = db.query(HistorySnapshot).filter(HistorySnapshot.fact_type.in_(types))
    rows = query.order_by(HistorySnapshot.captured_at.asc(), HistorySnapshot.id.asc()).all()
    if user_ids is None:
        return rows
    allowed = {str(uid) for uid in user_ids}
    filtered: list[HistorySnapshot] = []
    for row in rows:
        payload = _payload(row)
        uid = payload.get("用户ID") or payload.get("作者ID")
        if uid is not None and str(uid) in allowed:
            filtered.append(row)
    return filtered


def history_attempt_totals(
    db: Session,
    *,
    user_ids: Iterable[str] | None = None,
    announcement_ids: Iterable[int] | None = None,
) -> dict[str, Any]:
    """聚合历史答题记录，供练习统计与作业成绩回填。

    返回：
    - totals: {user_id: {"attempts": n, "correct": n}}
    - task_scores: {(user_id, announcement_id): score}
    - latest_correct: {(user_id, announcement_id, question_id): is_correct}
    """

    rows = _query_fact_rows(db, ("答题记录",), user_ids=user_ids)
    allowed_announcements = None
    if announcement_ids is not None:
        allowed_announcements = {int(item) for item in announcement_ids}

    seen: set[tuple[str, str]] = set()
    totals: dict[str, dict[str, int]] = {}
    latest_correct: dict[tuple[str, int, int], bool] = {}
    correct_counts: dict[tuple[str, int], int] = {}
    question_ids_by_task: dict[int, set[int]] = {}

    for row in rows:
        key = _fact_key(row)
        if key in seen:
            continue
        seen.add(key)
        payload = _payload(row)
        user_id = str(payload.get("用户ID") or "")
        if not user_id:
            continue
        announcement_id = _as_int(payload.get("作业ID"))
        question_id = _as_int(payload.get("题目ID"))
        if allowed_announcements is not None:
            if announcement_id is None or announcement_id not in allowed_announcements:
                continue

        bucket = totals.setdefault(user_id, {"attempts": 0, "correct": 0})
        bucket["attempts"] += 1
        is_correct = _as_bool(payload.get("是否正确"))
        if is_correct:
            bucket["correct"] += 1

        if announcement_id is not None and question_id is not None:
            latest_correct[(user_id, announcement_id, question_id)] = is_correct
            question_ids_by_task.setdefault(announcement_id, set()).add(question_id)
            if is_correct:
                correct_counts[(user_id, announcement_id)] = (
                    correct_counts.get((user_id, announcement_id), 0) + 1
                )
            else:
                correct_counts.setdefault((user_id, announcement_id), 0)

    question_count_by_task: dict[int, int] = {}
    for row in _query_fact_rows(db, ("作业摘要", "作业题目上下文")):
        payload = _payload(row)
        announcement_id = _as_int(payload.get("作业ID"))
        if announcement_id is None:
            continue
        if allowed_announcements is not None and announcement_id not in allowed_announcements:
            continue
        if row.fact_type == "作业摘要":
            ids = payload.get("题目IDs") or []
            if isinstance(ids, list) and ids:
                question_count_by_task[announcement_id] = len(ids)
            else:
                count = _as_int(payload.get("题目数量"))
                if count is not None:
                    question_count_by_task[announcement_id] = count
        elif announcement_id not in question_count_by_task:
            question_ids_by_task.setdefault(announcement_id, set())
            qid = _as_int(payload.get("题目ID"))
            if qid is not None:
                question_ids_by_task[announcement_id].add(qid)

    for announcement_id, qids in question_ids_by_task.items():
        question_count_by_task.setdefault(announcement_id, len(qids))

    task_scores: dict[tuple[str, int], int] = {}
    for (user_id, announcement_id), correct_count in correct_counts.items():
        total_questions = question_count_by_task.get(announcement_id, 0)
        if total_questions <= 0:
            answered = {
                qid
                for (uid, aid, qid), _ in latest_correct.items()
                if uid == user_id and aid == announcement_id
            }
            total_questions = len(answered)
        if total_questions <= 0:
            task_scores[(user_id, announcement_id)] = 0
        else:
            task_scores[(user_id, announcement_id)] = min(
                100, round(correct_count / total_questions * 100)
            )

    return {
        "totals": totals,
        "task_scores": task_scores,
        "latest_correct": latest_correct,
        "question_count_by_task": question_count_by_task,
    }


def history_completion_rows(
    db: Session,
    *,
    user_ids: Iterable[str] | None = None,
    announcement_ids: Iterable[int] | None = None,
    teacher_id: str | None = None,
    course_id: int | None = None,
) -> list[dict[str, Any]]:
    """读取历史作业完成记录，映射为报表 DTO。"""

    rows = _query_fact_rows(db, ("作业完成",), user_ids=user_ids)
    allowed_announcements = None
    if announcement_ids is not None:
        allowed_announcements = {int(item) for item in announcement_ids}

    meta_by_announcement: dict[int, dict[str, Any]] = {}
    for row in _query_fact_rows(db, ("作业摘要",)):
        payload = _payload(row)
        aid = _as_int(payload.get("作业ID"))
        if aid is None:
            continue
        meta_by_announcement[aid] = payload

    class_links: dict[int, set[int]] = {}
    class_names: dict[int, str] = {}
    for row in _query_fact_rows(db, ("作业班级关联",)):
        payload = _payload(row)
        aid = _as_int(payload.get("作业ID"))
        cid = _as_int(payload.get("班级ID"))
        if aid is None or cid is None:
            continue
        class_links.setdefault(aid, set()).add(cid)
        name = str(payload.get("班级名称") or "")
        if name:
            class_names[cid] = name

    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        key = _fact_key(row)
        if key in seen:
            continue
        seen.add(key)
        payload = _payload(row)
        user_id = str(payload.get("用户ID") or "")
        announcement_id = _as_int(payload.get("作业ID"))
        if not user_id or announcement_id is None:
            continue
        if allowed_announcements is not None and announcement_id not in allowed_announcements:
            continue

        meta = meta_by_announcement.get(announcement_id, {})
        row_teacher_id = str(payload.get("教师ID") or meta.get("教师ID") or "")
        row_course_id = _as_int(
            payload.get("课程ID") if payload.get("课程ID") is not None else meta.get("课程ID")
        )
        if teacher_id is not None and row_teacher_id and row_teacher_id != teacher_id:
            continue
        if course_id is not None and row_course_id is not None and row_course_id != course_id:
            continue

        title = str(payload.get("作业标题") or meta.get("作业标题") or f"历史作业#{announcement_id}")
        score = _as_score(payload.get("得分"))
        question_ids = meta.get("题目IDs") if isinstance(meta.get("题目IDs"), list) else []
        total_questions = len(question_ids) if question_ids else _as_int(meta.get("题目数量")) or 0
        result.append(
            {
                "user_id": user_id,
                "student_name": str(payload.get("学生姓名") or ""),
                "announcement_id": announcement_id,
                "announcement_title": title,
                "teacher_id": row_teacher_id,
                "course_id": row_course_id,
                "score": score,
                "total_questions": total_questions,
                "class_ids": sorted(class_links.get(announcement_id, set())),
                "class_names": [
                    class_names.get(cid, "")
                    for cid in sorted(class_links.get(announcement_id, set()))
                ],
                "cleanup_batch_id": row.cleanup_batch_id,
                "fact_id": row.fact_id,
                "source": "history_snapshot",
            }
        )
    return result


def history_task_catalog(
    db: Session,
    *,
    teacher_id: str | None = None,
    course_id: int | None = None,
    announcement_ids: Iterable[int] | None = None,
) -> list[dict[str, Any]]:
    """读取历史作业目录（标题、课程、班级关联、题目数）。"""

    allowed_announcements = None
    if announcement_ids is not None:
        allowed_announcements = {int(item) for item in announcement_ids}

    metas: dict[int, dict[str, Any]] = {}
    for row in _query_fact_rows(db, ("作业摘要",)):
        payload = _payload(row)
        aid = _as_int(payload.get("作业ID"))
        if aid is None:
            continue
        if allowed_announcements is not None and aid not in allowed_announcements:
            continue
        row_teacher_id = str(payload.get("教师ID") or "")
        row_course_id = _as_int(payload.get("课程ID"))
        if teacher_id is not None and row_teacher_id and row_teacher_id != teacher_id:
            continue
        if course_id is not None and row_course_id is not None and row_course_id != course_id:
            continue
        question_ids = payload.get("题目IDs") if isinstance(payload.get("题目IDs"), list) else []
        metas[aid] = {
            "announcement_id": aid,
            "title": str(payload.get("作业标题") or f"历史作业#{aid}"),
            "teacher_id": row_teacher_id,
            "course_id": row_course_id,
            "question_ids": list(question_ids),
            "total_questions": len(question_ids) if question_ids else _as_int(payload.get("题目数量")) or 0,
            "class_ids": set(),
            "class_names": {},
            "source": "history_snapshot",
        }

    for row in _query_fact_rows(db, ("作业班级关联",)):
        payload = _payload(row)
        aid = _as_int(payload.get("作业ID"))
        cid = _as_int(payload.get("班级ID"))
        if aid is None or cid is None:
            continue
        if aid not in metas:
            row_teacher_id = str(payload.get("教师ID") or "")
            row_course_id = _as_int(payload.get("课程ID"))
            if teacher_id is not None and row_teacher_id and row_teacher_id != teacher_id:
                continue
            if course_id is not None and row_course_id is not None and row_course_id != course_id:
                continue
            if allowed_announcements is not None and aid not in allowed_announcements:
                continue
            metas[aid] = {
                "announcement_id": aid,
                "title": str(payload.get("作业标题") or f"历史作业#{aid}"),
                "teacher_id": row_teacher_id,
                "course_id": row_course_id,
                "question_ids": [],
                "total_questions": 0,
                "class_ids": set(),
                "class_names": {},
                "source": "history_snapshot",
            }
        metas[aid]["class_ids"].add(cid)
        name = str(payload.get("班级名称") or "")
        if name:
            metas[aid]["class_names"][cid] = name

    result = []
    for aid, item in sorted(metas.items(), key=lambda pair: pair[0]):
        class_ids = sorted(item["class_ids"])
        result.append(
            {
                "announcement_id": aid,
                "title": item["title"],
                "teacher_id": item["teacher_id"],
                "course_id": item["course_id"],
                "question_ids": item["question_ids"],
                "total_questions": item["total_questions"],
                "class_ids": class_ids,
                "class_names": [item["class_names"].get(cid, "") for cid in class_ids],
                "source": "history_snapshot",
            }
        )
    return result


def history_project_rows(
    db: Session,
    *,
    user_ids: Iterable[str] | None = None,
    approved_only: bool = True,
) -> list[dict[str, Any]]:
    """读取历史作品摘要，供成长档案与统计使用。"""

    rows = _query_fact_rows(db, ("作品摘要", "用户作品"), user_ids=user_ids)
    seen: set[tuple[str, str]] = set()
    by_project: dict[int, dict[str, Any]] = {}
    for row in rows:
        key = _fact_key(row)
        if key in seen:
            continue
        seen.add(key)
        payload = _payload(row)
        project_id = _as_int(payload.get("作品ID") or row.resource_id)
        if project_id is None:
            continue
        status = str(payload.get("状态") or "approved")
        if approved_only and status and status != "approved":
            if row.fact_type != "用户作品":
                continue
        author_id = str(payload.get("作者ID") or payload.get("用户ID") or "")
        item = {
            "id": project_id,
            "title": str(payload.get("作品标题") or f"历史作品#{project_id}"),
            "author_id": author_id,
            "author_name": str(payload.get("作者姓名") or payload.get("用户姓名") or ""),
            "course_id": _as_int(payload.get("课程ID")),
            "major": str(payload.get("专业") or ""),
            "description": str(payload.get("描述") or ""),
            "tags": list(payload.get("标签") or []) if isinstance(payload.get("标签"), list) else [],
            "likes": int(payload.get("点赞数") or 0),
            "featured": bool(payload.get("是否精选")),
            "status": status or "approved",
            "date": str(payload.get("日期") or ""),
            # 清理后不返回可跳转详情 URL
            "video_url": "",
            "report_url": "",
            "image_url": "",
            "source": "history_snapshot",
        }
        existing = by_project.get(project_id)
        if existing is None or (
            row.fact_type == "作品摘要" and existing.get("source_fact") != "作品摘要"
        ):
            item["source_fact"] = row.fact_type
            by_project[project_id] = item

    result = []
    for item in by_project.values():
        item.pop("source_fact", None)
        result.append(item)
    result.sort(key=lambda row: row["id"])
    return result
