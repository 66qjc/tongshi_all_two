"""管理员公共课程服务。"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.cache import cache_result, invalidate_cache
from app.core.exceptions import BusinessException
from app.models.entities import Announcement, Course, CourseStage, Material, Question, QuizAttempt, StoredFile
from app.services.question_contribution_service import (
    list_question_contributions,
    record_question_contribution,
)
from app.services.question_bank_service import (
    compute_stem_hash,
    count_all_questions,
    find_duplicate_question,
    find_same_stem_question,
    rehome_questions_before_course_delete,
)
from app.services.public_course_sync_service import (
    delete_synced_materials,
    sync_course_name_to_copies,
    sync_material_to_course_copies,
)





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


@cache_result("course:public:list", ttl=300)
def list_public_courses(db: Session) -> list[Course]:
    """获取公共课程列表（缓存5分钟）"""
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
    if db.query(Course).filter(Course.name == name, Course.created_by == admin_id).first():
        raise BusinessException(400, "公共课程已存在")
    course = Course(name=name, created_by=admin_id, description=(description or "").strip(), is_public=True)
    db.add(course)
    db.commit()
    db.refresh(course)
    if course.question_bank_root_course_id is None:
        course.question_bank_root_course_id = course.id
        db.commit()
        db.refresh(course)
    # 清除公共课程列表缓存
    invalidate_cache("course:public:*")
    return course


def update_public_course(db: Session, course_id: int, name: str, description: str | None = None) -> Course | None:
    course = _get_public_course(db, course_id)
    if not course:
        return None
    course.name = name.strip()
    if description is not None:
        course.description = description.strip()
    sync_course_name_to_copies(db, course)
    db.commit()
    db.refresh(course)
    # 清除公共课程列表缓存
    invalidate_cache("course:public:*")
    return course


def delete_public_course(db: Session, course_id: int) -> bool:
    course = _get_public_course(db, course_id)
    if not course:
        return False
    # 全站共享题库：被删课程若是其他课程的共享根，阻止删除，避免全站题库失效
    is_referenced_root = db.query(Course).filter(
        Course.question_bank_root_course_id == course.id,
        Course.id != course.id,
        Course.deleted_at.is_(None),
    ).first() is not None
    if is_referenced_root:
        raise BusinessException(400, "该课程是共享题库根课程，请先迁移题库根后再删除")
    db.query(Course).filter(
        Course.question_bank_root_course_id == course.id,
        Course.id != course.id,
        Course.deleted_at.isnot(None),
    ).update({Course.question_bank_root_course_id: None}, synchronize_session=False)
    copies = db.query(Course).filter(Course.source_course_id == course.id).all()
    source_material_ids = [material.id for material in course.materials]
    source_stage_ids = [stage.id for stage in course.stages]
    # 全站共享题库：课程名下的题目需先转挂到共享根，避免随课程级联删除而误删全站共享题
    rehome_questions_before_course_delete(db, course)
    for copy in copies:
        copy.source_course_id = None
    if source_stage_ids:
        db.query(CourseStage).filter(
            CourseStage.source_stage_id.in_(source_stage_ids),
        ).update({CourseStage.source_stage_id: None}, synchronize_session=False)
    if source_material_ids:
        db.query(Material).filter(
            Material.source_material_id.in_(source_material_ids),
        ).update({Material.source_material_id: None}, synchronize_session=False)
    db.delete(course)
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
    """
    return (
        db.query(Question)
        .join(Course, Course.id == Question.course_id)
        .filter(
            Question.id == question_id,
            Question.deleted_at.is_(None),
            Course.deleted_at.is_(None),
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


def delete_public_material(db: Session, material_id: int) -> bool:
    material = db.query(Material).join(Course, Course.id == Material.course_id).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None),
        Course.is_public.is_(True),
        Course.deleted_at.is_(None),
    ).first()
    if not material:
        return False
    delete_synced_materials(db, material.id)
    db.delete(material)
    db.commit()
    return True


def list_public_questions(db: Session, course_id: int) -> list[Question]:
    course = _get_public_course(db, course_id)
    if not course:
        raise BusinessException(404, "公共课程不存在")
    # 全站共享题库：任意公共课程题库页都返回全站同一套活跃题
    return (
        db.query(Question)
        .join(Course, Course.id == Question.course_id)
        .filter(Question.deleted_at.is_(None), Course.deleted_at.is_(None))
        .order_by(Question.id)
        .all()
    )


def create_public_question(
    db: Session,
    course_id: int,
    data: dict,
    operator_id: str | None = None,
    operator_role: str = "admin",
) -> Question:
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
    # 题目原地保存，course_id 写所选公共课程
    question = Question(
        course_id=course.id,
        created_by=operator_id,
        stem_hash=stem_hash,
        **data,
    )
    db.add(question)
    db.flush()
    if operator_id:
        record_question_contribution(db, course, operator_id, operator_role, "create", 1)
    db.commit()
    db.refresh(question)
    return question


def update_public_question(db: Session, question_id: int, data: dict) -> Question | None:
    question = db.query(Question).join(Course, Course.id == Question.course_id).filter(
        Question.id == question_id,
        Question.deleted_at.is_(None),
        Course.deleted_at.is_(None),
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
    # 全站共享题库：题目不再复制到教师副本，无需同步
    db.commit()
    db.refresh(question)
    return question


def _purge_question_references(db: Session, question_ids: list[int]) -> None:
    """清理答题记录，并从作业 question_ids 中移除被删题目。"""
    if not question_ids:
        return
    id_set = set(question_ids)
    db.query(QuizAttempt).filter(
        QuizAttempt.question_id.in_(question_ids),
    ).delete(synchronize_session=False)

    # 兼容不同数据库：先筛可能命中的公告，再在 Python 中精确剔除。
    announcements = db.query(Announcement).filter(Announcement.question_ids.isnot(None)).all()
    for ann in announcements:
        current_ids = list(ann.question_ids or [])
        if not current_ids:
            continue
        filtered = [qid for qid in current_ids if qid not in id_set]
        if filtered != current_ids:
            ann.question_ids = filtered


def delete_public_question(db: Session, question_id: int) -> bool:
    question = get_public_question(db, question_id)
    if not question:
        return False
    # 全站共享题库：直接删题，先清理引用该题的答题记录和作业引用
    _purge_question_references(db, [question_id])
    db.delete(question)
    db.commit()
    return True


def delete_public_questions(db: Session, question_ids: list[int]) -> dict:
    """批量删除共享题库题目。"""
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
        .join(Course, Course.id == Question.course_id)
        .filter(
            Question.id.in_(unique_ids),
            Question.deleted_at.is_(None),
            Course.deleted_at.is_(None),
        )
        .all()
    )
    found_ids = [q.id for q in questions]
    missing_ids = [qid for qid in unique_ids if qid not in set(found_ids)]
    if not found_ids:
        raise BusinessException(404, "未找到可删除的题目")

    _purge_question_references(db, found_ids)
    for question in questions:
        db.delete(question)
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
        savepoint = None
        try:
            savepoint = db.begin_nested()
            q_type = str(_row_value(row, "题型", "type")).strip()
            stem = str(_row_value(row, "题干", "stem")).strip()
            if not stem:
                raise BusinessException(400, "题干为空")
            options = str(_row_value(row, "选项（选择题用 | 分隔）", "选项", "options")).strip()
            option_list = [x.strip() for x in options.split("|") if x.strip()] if options else []
            answer = str(_row_value(row, "答案", "answer")).strip()
            explanation = str(_row_value(row, "解析", "explanation")).strip()
            tags = _normalize_tags(_row_value(row, "标签", "课程标签", "tags", "course_tags"))
            if q_type not in {"choice", "fill", "multi_choice"}:
                raise BusinessException(400, "题型必须为 choice、fill 或 multi_choice")
            if q_type in {"choice", "multi_choice"} and not option_list:
                raise BusinessException(400, "选择题必须填写选项")
            stem_hash = compute_stem_hash(stem)
            existing = find_same_stem_question(db, stem)
            if existing:
                skips.append({"row": idx, "reason": f"题库中已存在相同题目（题干: {stem[:50]}），已跳过"})
                skip_count += 1
                savepoint.rollback()
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
                savepoint.rollback()
                continue
            question = Question(
                type=q_type, course_id=course.id, stem=stem,
                options=option_list, answer=answer, explanation=explanation, tags=tags,
                created_by=operator_id,
                stem_hash=stem_hash,
            )
            db.add(question)
            db.flush()
            savepoint.commit()
            success_count += 1
        except Exception as exc:
            if savepoint is not None and savepoint.is_active:
                savepoint.rollback()
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
