"""管理员独立共享题库服务。"""
from __future__ import annotations

import re

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BusinessException
from app.models.entities import Course, Question, QuestionContributionLog, User
from app.schemas.common import AuthUser
from app.services.audit_service import create_audit_log
from app.services.question_bank_service import (
    compute_stem_hash,
    find_duplicate_question,
    find_same_stem_question,
)
from app.services.question_contribution_service import record_question_contribution
from app.services.soft_delete_service import soft_delete


_IMPORT_COURSE_NAME_KEYS = ("课程名称", "课程", "course", "course_name", "课程名称（可选）")


def _normalize_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[,，、|/；;]+", str(value))
    seen = set()
    tags = []
    for item in raw_items:
        tag = str(item).strip()
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def _row_value(row: dict, *keys: str):
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return ""


def _resolve_import_course_by_name(db: Session, course_name: str) -> Course:
    """按名称解析唯一的活跃公共课程，避免同名课程被任意挂载。"""
    public_courses = (
        db.query(Course)
        .filter(
            Course.name == course_name,
            Course.is_public.is_(True),
            Course.deleted_at.is_(None),
        )
        .all()
    )
    if len(public_courses) == 1:
        return public_courses[0]
    if len(public_courses) > 1:
        raise BusinessException(400, f"课程名称“{course_name}”匹配到多门活跃公共课程，请使用唯一课程名称")

    active_courses = (
        db.query(Course)
        .filter(Course.name == course_name, Course.deleted_at.is_(None))
        .all()
    )
    if active_courses:
        raise BusinessException(400, f"课程名称“{course_name}”不是活跃公共课程")
    raise BusinessException(400, f"未找到名称为“{course_name}”的活跃公共课程")


def mount_course_state(question: Question) -> str:
    if question.course_id is None:
        snapshot = (question.mount_course_name_snapshot or "").strip()
        return "purged" if snapshot else "none"
    course = question.course
    if course is None:
        return "purged"
    if course.deleted_at is not None:
        return "soft_deleted"
    return "active"


def format_question(question: Question) -> dict:
    course = question.course
    creator = getattr(question, "creator", None)
    state = mount_course_state(question)
    snapshot = (question.mount_course_name_snapshot or "").strip()
    if state == "soft_deleted" and course is not None:
        course_name = f"{course.name}（已删除）"
    elif state == "purged":
        course_name = snapshot or "原挂载课程已清理"
    elif state == "none":
        course_name = "独立题库"
    else:
        course_name = course.name if course else snapshot
    return {
        "id": question.id,
        "type": question.type,
        "course_id": question.course_id,
        "course_name": course_name,
        "mount_course_state": state,
        "mount_course_name_snapshot": snapshot,
        "stem": question.stem,
        "options": question.options or [],
        "answer": question.answer,
        "explanation": question.explanation or "",
        "tags": question.tags or [],
        "source_question_id": question.source_question_id,
        "is_synced": bool(question.source_question_id),
        "created_by": question.created_by,
        "creator_name": creator.name if creator else None,
        "star_rating": question.star_rating if question.star_rating is not None else 3,
    }


def list_questions(
    db: Session,
    *,
    type_: str | None = None,
    keyword: str | None = None,
    tag: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Question], int, int, int]:
    safe_page = max(page or 1, 1)
    safe_page_size = max(min(page_size or 20, 100), 1)
    query = (
        db.query(Question)
        .options(joinedload(Question.creator), joinedload(Question.course))
        .filter(Question.deleted_at.is_(None))
    )
    if type_:
        query = query.filter(Question.type == type_)
    if keyword:
        query = query.filter(Question.stem.ilike(f"%{keyword.strip()}%"))
    tag_keyword = (tag or "").strip()
    if tag_keyword:
        query = query.filter(cast(Question.tags, String).ilike(f"%{tag_keyword}%"))
    total = query.count()
    items = (
        query.order_by(Question.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return items, total, safe_page, safe_page_size


def create_question(
    db: Session,
    data: dict,
    operator: AuthUser,
    mount_course_id: int | None = None,
) -> Question:
    course = None
    if mount_course_id is not None:
        course = (
            db.query(Course)
            .filter(
                Course.id == mount_course_id,
                Course.is_public.is_(True),
                Course.deleted_at.is_(None),
            )
            .first()
        )
        if not course:
            raise BusinessException(404, "挂载公共课程不存在")

    payload = dict(data)
    payload["tags"] = _normalize_tags(payload.get("tags"))
    stem = str(payload.get("stem") or "")
    stem_hash = compute_stem_hash(stem)
    existing = find_same_stem_question(db, stem)
    if existing:
        raise BusinessException(400, f"题库中已存在相同题目（ID: {existing.id}），请勿重复添加")
    duplicate = find_duplicate_question(
        db,
        payload["type"],
        payload["stem"],
        payload.get("options"),
        payload["answer"],
    )
    if duplicate:
        raise BusinessException(400, "题库中已存在相同题目")

    question = Question(
        course_id=course.id if course else None,
        created_by=operator.id,
        stem_hash=stem_hash,
        mount_course_name_snapshot=(course.name if course else "") or "",
        **payload,
    )
    db.add(question)
    db.flush()
    if course is not None:
        record_question_contribution(db, course, operator.id, operator.role, "create", 1)
    else:
        record_question_contribution(db, None, operator.id, operator.role, "create", 1)
    create_audit_log(
        db,
        user=operator,
        action="question.create",
        resource_type="questions",
        resource_id=question.id,
        resource_name=(question.stem or "")[:256],
        details={
            "入口": "独立题库",
            "挂载课程ID": question.course_id,
        },
    )
    db.commit()
    db.refresh(question)
    return question


def update_question(db: Session, question_id: int, data: dict, operator: AuthUser) -> Question | None:
    question = (
        db.query(Question)
        .options(joinedload(Question.creator), joinedload(Question.course))
        .filter(Question.id == question_id, Question.deleted_at.is_(None))
        .first()
    )
    if not question:
        return None
    merged = {
        "type": data.get("type", question.type),
        "stem": data.get("stem", question.stem),
        "options": data.get("options", list(question.options or [])),
        "answer": data.get("answer", question.answer),
    }
    stem_hash = compute_stem_hash(str(merged["stem"] or ""))
    existing = find_same_stem_question(db, str(merged["stem"] or ""), exclude_question_id=question.id)
    if existing:
        raise BusinessException(400, f"题库中已存在相同题目（ID: {existing.id}），请勿重复添加")
    duplicate = find_duplicate_question(
        db,
        merged["type"],
        merged["stem"],
        merged["options"],
        merged["answer"],
        exclude_question_id=question.id,
    )
    if duplicate:
        raise BusinessException(400, "题库中已存在相同题目")

    protected = {"id", "course_id", "source_question_id", "created_at", "created_by", "mount_course_name_snapshot"}
    for key, value in data.items():
        if key in protected:
            continue
        if value is not None and hasattr(question, key):
            setattr(question, key, _normalize_tags(value) if key == "tags" else value)
    question.stem_hash = stem_hash
    create_audit_log(
        db,
        user=operator,
        action="question.update",
        resource_type="questions",
        resource_id=question.id,
        resource_name=(question.stem or "")[:256],
        details={"入口": "独立题库", "挂载课程ID": question.course_id},
    )
    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, question_id: int, operator: AuthUser) -> bool:
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.deleted_at.is_(None))
        .first()
    )
    if not question:
        return False
    soft_delete(db, question, operator, action="question.delete")
    db.commit()
    return True


def delete_questions(db: Session, question_ids: list[int], operator: AuthUser) -> dict:
    unique_ids: list[int] = []
    seen: set[int] = set()
    for raw in question_ids or []:
        try:
            qid = int(raw)
        except (TypeError, ValueError):
            continue
        if qid <= 0 or qid in seen:
            continue
        seen.add(qid)
        unique_ids.append(qid)
    if not unique_ids:
        raise BusinessException(400, "请选择要删除的题目")
    questions = (
        db.query(Question)
        .filter(Question.id.in_(unique_ids), Question.deleted_at.is_(None))
        .all()
    )
    found_ids = [q.id for q in questions]
    missing_ids = [qid for qid in unique_ids if qid not in set(found_ids)]
    if not found_ids:
        raise BusinessException(404, "未找到可删除的题目")
    for question in questions:
        soft_delete(db, question, operator, action="question.delete")
    db.commit()
    return {
        "deleted_count": len(found_ids),
        "deleted_ids": found_ids,
        "missing_ids": missing_ids,
    }


def import_questions(
    db: Session,
    rows: list[dict],
    operator: AuthUser,
    mount_course_id: int | None = None,
) -> dict:
    default_course = None
    if mount_course_id is not None:
        default_course = (
            db.query(Course)
            .filter(
                Course.id == mount_course_id,
                Course.is_public.is_(True),
                Course.deleted_at.is_(None),
            )
            .first()
        )
        if not default_course:
            raise BusinessException(404, "挂载公共课程不存在")

    success_count = 0
    fail_count = 0
    skip_count = 0
    errors: list[dict] = []
    skips: list[dict] = []
    contribution_counts: dict[int | None, int] = {}
    contribution_courses: dict[int, Course] = {}
    for idx, row in enumerate(rows, start=2):
        try:
            q_type = str(_row_value(row, "题型", "type")).strip()
            stem = str(_row_value(row, "题干", "stem")).strip()
            if not stem:
                raise BusinessException(400, "题干为空")
            options = str(_row_value(row, "选项（选择题用 | 分隔）", "选项", "options")).strip()
            option_list = [x.strip() for x in options.split("|") if x.strip()] if options else []
            answer = str(_row_value(row, "答案", "answer")).strip()
            if not answer:
                raise BusinessException(400, "答案不能为空")
            explanation = str(_row_value(row, "解析", "explanation")).strip()
            tags = _normalize_tags(_row_value(row, "标签", "课程标签", "tags", "course_tags"))
            if not tags:
                raise BusinessException(400, "标签不能为空")
            if q_type not in {"choice", "fill", "multi_choice"}:
                raise BusinessException(400, "题型必须为 choice、fill 或 multi_choice")
            if q_type in {"choice", "multi_choice"} and not option_list:
                raise BusinessException(400, "选择题必须填写选项")
            course_name = str(_row_value(row, *_IMPORT_COURSE_NAME_KEYS)).strip()
            target_course = _resolve_import_course_by_name(db, course_name) if course_name else default_course
            stem_hash = compute_stem_hash(stem)
            if find_same_stem_question(db, stem) or find_duplicate_question(db, q_type, stem, option_list, answer):
                skips.append({"row": idx, "reason": f"题库中已存在相同题目（题干: {stem[:50]}），已跳过"})
                skip_count += 1
                continue
            question = Question(
                type=q_type,
                course_id=target_course.id if target_course else None,
                stem=stem,
                options=option_list,
                answer=answer,
                explanation=explanation,
                tags=tags,
                created_by=operator.id,
                stem_hash=stem_hash,
                mount_course_name_snapshot=(target_course.name if target_course else "") or "",
            )
            with db.begin_nested():
                db.add(question)
                db.flush()
            success_count += 1
            contribution_key = target_course.id if target_course else None
            contribution_counts[contribution_key] = contribution_counts.get(contribution_key, 0) + 1
            if target_course:
                contribution_courses[target_course.id] = target_course
        except Exception as exc:  # noqa: BLE001
            fail_count += 1
            errors.append({"row": idx, "reason": str(exc)})

    for course_id, question_count in contribution_counts.items():
        record_question_contribution(
            db,
            contribution_courses.get(course_id) if course_id is not None else None,
            operator.id,
            operator.role,
            "import",
            question_count,
        )
    db.commit()
    return {
        "success_count": success_count,
        "skip_count": skip_count,
        "fail_count": fail_count,
        "skips": skips,
        "errors": errors,
    }


def list_contributions(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[QuestionContributionLog], int, int, int]:
    safe_page = max(page or 1, 1)
    safe_page_size = max(min(page_size or 20, 100), 1)
    query = db.query(QuestionContributionLog)
    total = query.count()
    items = (
        query.order_by(
            QuestionContributionLog.created_at.desc(),
            QuestionContributionLog.id.desc(),
        )
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return items, total, safe_page, safe_page_size


def format_contribution(log: QuestionContributionLog) -> dict:
    return {
        "id": log.id,
        "public_course_id": log.public_course_id,
        "public_course_name": log.public_course_name or "独立题库",
        "operator_id": log.operator_id,
        "operator_name": log.operator_name,
        "operator_role": log.operator_role,
        "action": log.action,
        "question_count": log.question_count,
        "created_at": log.created_at.isoformat() if log.created_at else "",
    }
