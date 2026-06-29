"""管理员公共课程服务。"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Course, CourseStage, Material, Question, QuizAttempt, StoredFile
from app.services.question_contribution_service import (
    list_question_contributions,
    record_question_contribution,
)
from app.services.question_bank_service import (
    count_all_questions,
    find_duplicate_question,
    get_shared_question_bank_root_course,
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
    return db.query(Course).filter(Course.id == course_id, Course.is_public.is_(True)).first()


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
    return db.query(Course).filter(Course.is_public.is_(True)).order_by(Course.id.desc()).all()


def get_course_sync_status(db: Session, course: Course) -> dict:
    """计算公共课程的同步状态摘要。"""
    copies = db.query(Course).filter(Course.source_course_id == course.id).all()
    sync_copy_count = len(copies)
    synced_material_count = db.query(Material).filter(
        Material.source_material_id.in_([m.id for m in course.materials])
    ).count() if course.materials else 0
    synced_question_count = 0

    total_items = len(course.materials) + len(course.questions)
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
    return course


def delete_public_course(db: Session, course_id: int) -> bool:
    course = _get_public_course(db, course_id)
    if not course:
        return False
    # 全站共享题库：被删课程若是其他课程的共享根，阻止删除，避免全站题库失效
    is_referenced_root = db.query(Course).filter(
        Course.question_bank_root_course_id == course.id,
        Course.id != course.id,
    ).first() is not None
    if is_referenced_root:
        raise BusinessException(400, "该课程是共享题库根课程，请先迁移题库根后再删除")
    copies = db.query(Course).filter(Course.source_course_id == course.id).all()
    source_material_ids = [material.id for material in course.materials]
    source_stage_ids = [stage.id for stage in course.stages]
    # 全站共享题库：课程名下的题目需先转挂到共享根，避免随课程级联删除而误删全站共享题
    _reattach_questions_to_shared_root(db, course)
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
    return True


def _reattach_questions_to_shared_root(db: Session, course: Course) -> None:
    """删除公共课程前，把其名下题目转挂到另一门课程，避免级联删除全站共享题。

    优先转挂到共享根课程；若被删课程恰好是当前选出的根，则退而选择其他任意课程承接。
    """
    questions = db.query(Question).filter(Question.course_id == course.id).all()
    if not questions:
        return
    target = db.query(Course).filter(Course.id != course.id).order_by(
        Course.is_public.desc(),
        Course.id.asc(),
    ).first()
    if target is None:
        # 全站只剩这一门课，无处转挂，题目随课程一并删除
        return
    for question in questions:
        question.course_id = target.id
    db.flush()


def get_public_material(db: Session, material_id: int) -> Material | None:
    """查询公共课程资料（仅查存在性，不触发同步）。"""
    return db.query(Material).join(Course).filter(
        Material.id == material_id,
        Course.is_public.is_(True),
    ).first()


def get_public_question(db: Session, question_id: int) -> Question | None:
    """查询公共课程题目（仅查存在性，不触发同步）。"""
    return db.query(Question).join(Course).filter(
        Question.id == question_id,
        Course.is_public.is_(True),
    ).first()


def list_public_materials(db: Session, course_id: int) -> list[Material]:
    course = _get_public_course(db, course_id)
    if not course:
        raise BusinessException(404, "公共课程不存在")
    return db.query(Material).filter(Material.course_id == course_id).order_by(Material.id).all()


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
    material = db.query(Material).join(Course).filter(
        Material.id == material_id,
        Course.is_public.is_(True),
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
    material = db.query(Material).join(Course).filter(
        Material.id == material_id,
        Course.is_public.is_(True),
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
    # 全站共享题库：任意公共课程题库页都返回全站同一套题
    return db.query(Question).order_by(Question.id).all()


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
    question = Question(course_id=course.id, **data)
    db.add(question)
    db.flush()
    if operator_id:
        record_question_contribution(db, course, operator_id, operator_role, "create", 1)
    db.commit()
    db.refresh(question)
    return question


def update_public_question(db: Session, question_id: int, data: dict) -> Question | None:
    question = db.query(Question).join(Course).filter(
        Question.id == question_id,
        Course.is_public.is_(True),
    ).first()
    if not question:
        return None
    _PROTECTED_FIELDS = {"id", "course_id", "source_question_id", "created_at"}
    for key, value in data.items():
        if key in _PROTECTED_FIELDS:
            continue
        if value is not None and hasattr(question, key):
            setattr(question, key, _normalize_tags(value) if key == "tags" else value)
    # 全站共享题库：题目不再复制到教师副本，无需同步
    db.commit()
    db.refresh(question)
    return question


def delete_public_question(db: Session, question_id: int) -> bool:
    question = db.query(Question).join(Course).filter(
        Question.id == question_id,
        Course.is_public.is_(True),
    ).first()
    if not question:
        return False
    # 全站共享题库：直接删题，先清理引用该题的答题记录
    db.query(QuizAttempt).filter(
        QuizAttempt.question_id == question_id,
    ).delete(synchronize_session=False)
    db.delete(question)
    db.commit()
    return True


def get_course_by_id(db: Session, course_id: int) -> Course | None:
    """按 ID 查询课程（不限公共标记）。"""
    return db.query(Course).filter(Course.id == course_id).first()


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
    """批量导入题目到公共课程，并同步到教师副本。"""
    course = _get_public_course(db, course_id)
    if not course:
        raise BusinessException(404, "公共课程不存在")
    success_count = 0
    fail_count = 0
    errors = []
    for idx, row in enumerate(rows, start=2):
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
            # 全站共享题库：查重范围为全站所有题目
            duplicate = find_duplicate_question(
                db,
                q_type,
                stem,
                option_list,
                answer,
            )
            if duplicate:
                errors.append({"row": idx, "reason": f"题库中已存在相同题目（题干: {stem[:50]}），已跳过"})
                continue
            question = Question(
                type=q_type, course_id=course.id, stem=stem,
                options=option_list, answer=answer, explanation=explanation, tags=tags,
            )
            db.add(question)
            db.flush()
            savepoint.commit()
            success_count += 1
        except Exception as exc:
            fail_count += 1
            errors.append({"row": idx, "reason": str(exc)})
    if operator_id and success_count > 0:
        record_question_contribution(db, course, operator_id, operator_role, "import", success_count)
    db.commit()
    return {"success_count": success_count, "fail_count": fail_count, "errors": errors}
