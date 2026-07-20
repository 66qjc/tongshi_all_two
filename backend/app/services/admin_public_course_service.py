"""管理员公共课程服务。"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.cache import invalidate_cache
from app.core.exceptions import BusinessException
from app.models.entities import Course, CourseStage, Material, Question, StoredFile
from app.schemas.common import AuthUser
from app.services.question_contribution_service import (
    list_question_contributions,
    record_question_contribution,
)
from app.services.question_bank_service import (
    compute_stem_hash,
    count_all_questions,
    find_duplicate_question,
    find_same_stem_question,
)
from app.services.public_course_sync_service import (
    sync_course_name_to_copies,
    sync_material_to_course_copies,
)
from app.services.soft_delete_service import soft_delete





def _validate_material_file(db: Session, type_: str, file_id: int | None) -> None:
    """校验资料所选类型与上传文件一致，且 file_id 真实存在。"""
    if type_ not in {"video", "pdf"}:
        return
    if file_id is None:
        raise BusinessException(400, "视频/PDF 资料必须上传文件")
    stored = db.query(StoredFile).filter(StoredFile.id == file_id).first()
    if not stored:
        raise BusinessException(400, "关联文件不存在")
    ext = (stored.extension or Path(stored.original_name).suffix).lower()
    content_type = stored.content_type or ""
    if type_ == "pdf" and ext != ".pdf" and "pdf" not in content_type:
        raise BusinessException(400, "资料类型为 PDF，但上传文件不是 PDF")
    if type_ == "video" and ext not in {".mp4", ".webm", ".mov"} and not content_type.startswith("video/"):
        raise BusinessException(400, "资料类型为视频，但上传文件不是视频格式")

def _get_public_course(db: Session, course_id: int) -> Course | None:
    return db.query(Course).filter(
        Course.id == course_id,
        Course.is_public.is_(True),
        Course.deleted_at.is_(None),
    ).first()


def _validate_stage_id(db: Session, course_id: int, stage_id: int | None) -> None:
    """校验 stage_id 存在且属于指定课程，stage_id 为 None 时跳过。"""
    if stage_id is None:
        return
    stage = db.query(CourseStage).filter(
        CourseStage.id == stage_id,
        CourseStage.course_id == course_id,
    ).first()
    if not stage:
        raise BusinessException(400, "阶段不存在或不属于该课程")


def list_public_courses(db: Session) -> list[Course]:
    """获取公共课程列表。

    不再使用 ORM 对象缓存：返回值含 Session 绑定实体，JSON 缓存无效且键不稳定。
    """
    return db.query(Course).filter(
        Course.is_public.is_(True),
        Course.deleted_at.is_(None),
    ).order_by(Course.id.desc()).all()


def get_course_sync_status(db: Session, course: Course) -> dict:
    """计算公共课程的同步状态摘要。"""
    copies = db.query(Course).filter(
        Course.source_course_id == course.id,
        Course.deleted_at.is_(None),
    ).all()
    sync_copy_count = len(copies)
    active_source_material_ids = [
        material.id for material in course.materials if material.deleted_at is None
    ]
    synced_material_count = (
        db.query(Material)
        .join(Course, Course.id == Material.course_id)
        .filter(
            Material.source_material_id.in_(active_source_material_ids),
            Material.deleted_at.is_(None),
            Course.source_course_id == course.id,
            Course.deleted_at.is_(None),
        )
        .count()
        if active_source_material_ids
        else 0
    )
    synced_question_count = 0

    # 共享题库题目不再复制到课程副本，同步分母只统计实际镜像的活跃资料。
    total_items = len(active_source_material_ids)
    synced_items = synced_material_count + synced_question_count
    if total_items == 0 or sync_copy_count == 0:
        sync_status = "not_synced"
    elif synced_items >= total_items * sync_copy_count:
        sync_status = "synced"
    else:
        sync_status = "partial"

    return {
        "sync_copy_count": sync_copy_count,
        "synced_material_count": synced_material_count,
        "synced_question_count": synced_question_count,
        "sync_status": sync_status,
    }


def create_public_course(db: Session, name: str, admin_id: str, description: str = "") -> Course:
    if db.query(Course).filter(
        Course.name == name,
        Course.created_by == admin_id,
        Course.deleted_at.is_(None),
    ).first():
        raise BusinessException(400, "公共课程已存在")
    # 不再写入 question_bank_root_course_id；该列仅兼容保留，不参与业务。
    course = Course(
        name=name,
        created_by=admin_id,
        description=(description or "").strip(),
        is_public=True,
    )
    db.add(course)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise BusinessException(400, "公共课程已存在")
    db.commit()
    db.refresh(course)
    # 清除公共课程列表缓存
    invalidate_cache("course:public:*")
    return course

def update_public_course(db: Session, course_id: int, name: str, description: str | None = None) -> Course | None:
    course = _get_public_course(db, course_id)
    if not course:
        return None
    normalized_name = name.strip()
    duplicate = db.query(Course).filter(
        Course.name == normalized_name,
        Course.created_by == course.created_by,
        Course.deleted_at.is_(None),
        Course.id != course.id,
    ).first()
    if duplicate:
        raise BusinessException(400, "公共课程已存在")

    course.name = normalized_name
    if description is not None:
        course.description = description.strip()
    try:
        # 先校验公共课程自身，再同步并校验所有教师副本，任一冲突则整体回滚。
        db.flush()
        sync_course_name_to_copies(db, course)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise BusinessException(400, "公共课程或教师课程中已存在同名课程")

    db.query(Question).filter(
        Question.course_id == course.id,
        Question.deleted_at.is_(None),
    ).update({Question.mount_course_name_snapshot: course.name}, synchronize_session=False)
    db.commit()
    db.refresh(course)
    # 清除公共课程列表缓存
    invalidate_cache("course:public:*")
    return course

def delete_public_course(db: Session, course_id: int, operator: AuthUser | None = None) -> bool:
    """软删除公共课程，不转挂题目，不破坏阶段/同步引用。"""
    course = _get_public_course(db, course_id)
    if not course:
        return False
    # 历史字段 question_bank_root_course_id 不再阻断删除；共享题独立于课程生命周期。
    actor = operator or AuthUser(id="admin", name="", role="admin")
    soft_delete(
        db,
        course,
        actor,
        action="course.delete",
    )
    db.commit()
    # 清除公共课程列表缓存
    invalidate_cache("course:public:*")
    return True


def get_public_material(db: Session, material_id: int) -> Material | None:
    """查询公共课程资料（仅查存在性，不触发同步）。"""
    return db.query(Material).join(Course, Course.id == Material.course_id).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None),
        Course.is_public.is_(True),
        Course.deleted_at.is_(None),
    ).first()


def get_public_question(db: Session, question_id: int) -> Question | None:
    """查询共享题库题目。

    管理端题库页展示的是全站共享题，不再要求题目必须挂在公共课程上。
    活跃性只看题目自身 deleted_at，课程软删不得隐藏题目。
    """
    return (
        db.query(Question)
        .filter(
            Question.id == question_id,
            Question.deleted_at.is_(None),
        )
        .first()
    )


def list_public_materials(db: Session, course_id: int) -> list[Material]:
    course = _get_public_course(db, course_id)
    if not course:
        raise BusinessException(404, "公共课程不存在")
    return db.query(Material).filter(
        Material.course_id == course_id,
        Material.deleted_at.is_(None),
    ).order_by(Material.id).all()


def create_public_material(db: Session, course_id: int, data: dict) -> Material:
    course = _get_public_course(db, course_id)
    if not course:
        raise BusinessException(404, "公共课程不存在")
    _validate_material_file(db, data.get("type", ""), data.get("file_id"))
    _validate_stage_id(db, course_id, data.get("stage_id"))
    material = Material(
        course_id=course.id,
        date=datetime.now().strftime("%Y-%m-%d"),
        **data,
    )
    db.add(material)
    db.flush()
    sync_material_to_course_copies(db, material)
    from app.services.material_preview_service import bootstrap_material_preview
    # 公共课 PDF 上传后立即生成摘要，供游客公开阅读页展示。
    bootstrap_material_preview(db, material)
    db.commit()
    db.refresh(material)
    return material


def update_public_material(db: Session, material_id: int, data: dict) -> Material | None:
    material = db.query(Material).join(Course, Course.id == Material.course_id).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None),
        Course.is_public.is_(True),
        Course.deleted_at.is_(None),
    ).first()
    if not material:
        return None
    if data.get("file_id") is not None:
        new_type = data.get("type", material.type)
        _validate_material_file(db, new_type, data.get("file_id"))
    if "stage_id" in data:
        _validate_stage_id(db, material.course_id, data.get("stage_id"))
    _MATERIAL_PROTECTED = {"id", "course_id", "source_material_id", "created_at"}
    for key, value in data.items():
        if key in _MATERIAL_PROTECTED:
            continue
        if hasattr(material, key):
            if value is not None or key in ("stage_id",):
                setattr(material, key, value)
    sync_material_to_course_copies(db, material)
    db.commit()
    db.refresh(material)
    return material


def delete_public_material(db: Session, material_id: int, operator: AuthUser | None = None) -> bool:
    """软删除公共资料，保留文件、预览与教师副本引用。"""
    material = db.query(Material).join(Course, Course.id == Material.course_id).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None),
        Course.is_public.is_(True),
        Course.deleted_at.is_(None),
    ).first()
    if not material:
        return False
    actor = operator or AuthUser(id="admin", name="", role="admin")
    soft_delete(
        db,
        material,
        actor,
        action="material.delete",
    )
    db.commit()
    return True


def list_public_questions(db: Session, course_id: int) -> list[Question]:
    course = _get_public_course(db, course_id)
    if not course:
        raise BusinessException(404, "公共课程不存在")
    # 全站共享题库：任意公共课程题库页都返回全站同一套活跃题。
    # 课程只是管理入口，不得因挂载课软删而过滤题目。
    return (
        db.query(Question)
        .options(joinedload(Question.creator), joinedload(Question.course))
        .filter(Question.deleted_at.is_(None))
        .order_by(Question.id)
        .all()
    )


def create_public_question(
    db: Session,
    course_id: int,
    data: dict,
    operator_id: str | None = None,
    operator_role: str = "admin",
    operator: AuthUser | None = None,
) -> Question:
    from app.services.audit_service import create_audit_log

    course = _get_public_course(db, course_id)
    if not course:
        raise BusinessException(404, "公共课程不存在")
    data["tags"] = _normalize_tags(data.get("tags"))
    stem_hash = compute_stem_hash(str(data.get("stem") or ""))
    existing = find_same_stem_question(db, str(data.get("stem") or ""))
    if existing:
        raise BusinessException(400, f"题库中已存在相同题目（ID: {existing.id}），请勿重复添加")
    # 全站共享题库：查重范围为全站所有题目
    duplicate = find_duplicate_question(
        db,
        data["type"],
        data["stem"],
        data.get("options"),
        data["answer"],
    )
    if duplicate:
        raise BusinessException(400, "题库中已存在相同题目")
    actor_id = operator.id if operator else operator_id
    # 题目原地保存，course_id 写所选公共课程，并固化挂载名称快照
    question = Question(
        course_id=course.id,
        created_by=actor_id,
        stem_hash=stem_hash,
        mount_course_name_snapshot=course.name or "",
        **data,
    )
    db.add(question)
    db.flush()
    if actor_id:
        record_question_contribution(db, course, actor_id, operator_role, "create", 1)
    create_audit_log(
        db,
        user=operator or AuthUser(id=actor_id or "admin", name="", role=operator_role),
        action="question.create",
        resource_type="questions",
        resource_id=question.id,
        resource_name=(question.stem or "")[:256],
        details={"入口课程ID": course.id, "挂载课程ID": question.course_id},
    )
    db.commit()
    db.refresh(question)
    return question


def update_public_question(
    db: Session,
    question_id: int,
    data: dict,
    operator: AuthUser | None = None,
) -> Question | None:
    from app.services.audit_service import create_audit_log

    question = db.query(Question).filter(
        Question.id == question_id,
        Question.deleted_at.is_(None),
    ).first()
    if not question:
        return None
    merged_data = {
        "type": data.get("type", question.type),
        "stem": data.get("stem", question.stem),
        "options": data.get("options", list(question.options or [])),
        "answer": data.get("answer", question.answer),
    }
    stem_hash = compute_stem_hash(str(merged_data["stem"] or ""))
    existing = find_same_stem_question(
        db,
        str(merged_data["stem"] or ""),
        exclude_question_id=question.id,
    )
    if existing:
        raise BusinessException(400, f"题库中已存在相同题目（ID: {existing.id}），请勿重复添加")
    duplicate = find_duplicate_question(
        db,
        merged_data["type"],
        merged_data["stem"],
        merged_data["options"],
        merged_data["answer"],
        exclude_question_id=question.id,
    )
    if duplicate:
        raise BusinessException(400, "题库中已存在相同题目")
    _PROTECTED_FIELDS = {"id", "course_id", "source_question_id", "created_at"}
    for key, value in data.items():
        if key in _PROTECTED_FIELDS:
            continue
        if value is not None and hasattr(question, key):
            setattr(question, key, _normalize_tags(value) if key == "tags" else value)
    question.stem_hash = stem_hash
    create_audit_log(
        db,
        user=operator or AuthUser(id="admin", name="", role="admin"),
        action="question.update",
        resource_type="questions",
        resource_id=question.id,
        resource_name=(question.stem or "")[:256],
        details={"挂载课程ID": question.course_id},
    )
    # 全站共享题库：题目不再复制到教师副本，无需同步
    db.commit()
    db.refresh(question)
    return question


def delete_public_question(
    db: Session,
    question_id: int,
    operator: AuthUser | None = None,
) -> bool:
    """软删除共享题库题目，保留答题记录与作业题目列表。"""
    question = get_public_question(db, question_id)
    if not question:
        return False
    actor = operator or AuthUser(id="admin", name="", role="admin")
    soft_delete(
        db,
        question,
        actor,
        action="question.delete",
    )
    db.commit()
    return True


def delete_public_questions(
    db: Session,
    question_ids: list[int],
    operator: AuthUser | None = None,
) -> dict:
    """批量软删除共享题库题目。"""
    unique_ids = []
    seen = set()
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
        .filter(
            Question.id.in_(unique_ids),
            Question.deleted_at.is_(None),
        )
        .all()
    )
    found_ids = [q.id for q in questions]
    missing_ids = [qid for qid in unique_ids if qid not in set(found_ids)]
    if not found_ids:
        raise BusinessException(404, "未找到可删除的题目")

    actor = operator or AuthUser(id="admin", name="", role="admin")
    for question in questions:
        soft_delete(db, question, actor, action="question.delete")
    db.commit()
    return {
        "deleted_count": len(found_ids),
        "deleted_ids": found_ids,
        "missing_ids": missing_ids,
    }


def get_course_by_id(db: Session, course_id: int) -> Course | None:
    """按 ID 查询课程（不限公共标记）。"""
    return db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None),
    ).first()


def _row_value(row: dict, *keys: str):
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return ""


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


def import_questions_to_public_course(
    db: Session,
    course_id: int,
    rows: list[dict],
    operator_id: str | None = None,
    operator_role: str = "admin",
) -> dict:
    """通过公共课程入口批量导入题目到全站共享题库。"""
    course = _get_public_course(db, course_id)
    if not course:
        raise BusinessException(404, "公共课程不存在")
    success_count = 0
    skip_count = 0
    fail_count = 0
    skips = []
    errors = []
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
            stem_hash = compute_stem_hash(stem)
            existing = find_same_stem_question(db, stem)
            if existing:
                skips.append({"row": idx, "reason": f"题库中已存在相同题目（题干: {stem[:50]}），已跳过"})
                skip_count += 1
                continue
            # 全站共享题库：查重范围为全站所有题目
            duplicate = find_duplicate_question(
                db,
                q_type,
                stem,
                option_list,
                answer,
            )
            if duplicate:
                skips.append({"row": idx, "reason": f"题库中已存在相同题目（题干: {stem[:50]}），已跳过"})
                skip_count += 1
                continue
            question = Question(
                type=q_type, course_id=course.id, stem=stem,
                options=option_list, answer=answer, explanation=explanation, tags=tags,
                created_by=operator_id,
                stem_hash=stem_hash,
                mount_course_name_snapshot=course.name or "",
            )
            with db.begin_nested():
                db.add(question)
                db.flush()
            success_count += 1
        except Exception as exc:
            fail_count += 1
            errors.append({"row": idx, "reason": str(exc)})
    if operator_id and success_count > 0:
        record_question_contribution(db, course, operator_id, operator_role, "import", success_count)
    db.commit()
    return {
        "success_count": success_count,
        "skip_count": skip_count,
        "fail_count": fail_count,
        "skips": skips,
        "errors": errors,
    }
