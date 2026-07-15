"""共享题库辅助函数。"""
from __future__ import annotations

import hashlib
import re

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Course, Question


def compute_stem_hash(stem: str) -> str:
    """计算兼容现有数据的题干哈希。"""
    return hashlib.md5(stem.strip().lower().encode("utf-8")).hexdigest()


def _active_questions_query(db: Session):
    """返回题目和所属课程均未软删除的共享题库查询。"""
    return (
        db.query(Question)
        .join(Course, Course.id == Question.course_id)
        .filter(Question.deleted_at.is_(None), Course.deleted_at.is_(None))
    )


def find_same_stem_question(
    db: Session,
    stem: str,
    exclude_question_id: int | None = None,
) -> Question | None:
    """按兼容哈希语义查找同题干题目，仅检查活跃题目和活跃课程。"""
    normalized_stem = stem.strip().lower()
    stem_hash = compute_stem_hash(stem)
    query = _active_questions_query(db).filter(
        or_(
            Question.stem_hash == stem_hash,
            func.lower(func.trim(Question.stem)) == normalized_stem,
        )
    )
    if exclude_question_id is not None:
        query = query.filter(Question.id != exclude_question_id)
    return query.first()


def resolve_question_bank_course(db: Session, course: Course) -> Course:
    """解析课程所属的共享题库根课程。"""
    if course.question_bank_root_course_id is None:
        return course
    root = db.query(Course).filter(
        Course.id == course.question_bank_root_course_id,
        Course.deleted_at.is_(None),
    ).first()
    return root or course


def get_shared_question_bank_root_course(db: Session) -> Course | None:
    """获取当前系统内的共享题库根课程。"""
    root = db.query(Course).filter(
        Course.question_bank_root_course_id.is_(None),
        Course.deleted_at.is_(None),
    ).order_by(
        Course.is_public.desc(),
        Course.id.asc(),
    ).first()
    if root:
        return root

    referenced_root_id = db.query(Course.question_bank_root_course_id).filter(
        Course.question_bank_root_course_id.isnot(None),
        Course.deleted_at.is_(None),
    ).order_by(Course.id.asc()).first()
    if referenced_root_id and referenced_root_id[0] is not None:
        return db.query(Course).filter(
            Course.id == referenced_root_id[0],
            Course.deleted_at.is_(None),
        ).first()
    return None


def get_question_bank_course(db: Session, course: Course | None) -> Course | None:
    if course is None:
        return get_shared_question_bank_root_course(db)
    return resolve_question_bank_course(db, course)


def rehome_questions_before_course_delete(db: Session, course: Course) -> Course | None:
    """删除课程前把有效共享题转挂到另一门未删除课程。"""
    questions = db.query(Question).filter(
        Question.course_id == course.id,
        Question.deleted_at.is_(None),
    ).all()
    if not questions:
        return None

    target = db.query(Course).filter(
        Course.id != course.id,
        Course.deleted_at.is_(None),
    ).order_by(
        Course.is_public.desc(),
        Course.id.asc(),
    ).first()
    if target is None:
        raise BusinessException(400, "当前没有可承接共享题库的课程，暂时无法删除该课程")

    for question in questions:
        question.course_id = target.id
    db.flush()
    return target


def normalize_question_stem(stem: str) -> str:
    return re.sub(r"\s+", " ", str(stem).strip())


def normalize_question_options(options) -> list[str]:
    if options is None:
        return []
    if not isinstance(options, list):
        options = list(options)
    normalized: list[str] = []
    for item in options:
        value = str(item).strip()
        if value:
            normalized.append(value)
    return normalized


def normalize_question_answer(question_type: str, answer: str) -> str:
    text = re.sub(r"\s+", " ", str(answer).strip())
    if question_type == "multi_choice":
        letters = sorted({ch for ch in text.upper() if ch.isalpha()})
        return "".join(letters)
    return text


def build_question_fingerprint(question_type: str, stem: str, options, answer: str) -> tuple[str, str, tuple[str, ...], str]:
    normalized_options = tuple(normalize_question_options(options))
    return (
        str(question_type).strip(),
        normalize_question_stem(stem),
        normalized_options,
        normalize_question_answer(question_type, answer),
    )


def build_question_fingerprint_from_question(question: Question) -> tuple[str, str, tuple[str, ...], str]:
    return build_question_fingerprint(
        question.type,
        question.stem,
        list(question.options or []),
        question.answer,
    )


def collect_question_fingerprints(db: Session) -> set[tuple[str, str, tuple[str, ...], str]]:
    """收集全站共享题库已存在题目的指纹。"""
    fingerprints: set[tuple[str, str, tuple[str, ...], str]] = set()
    for question in _active_questions_query(db).all():
        fingerprints.add(build_question_fingerprint_from_question(question))
    return fingerprints


def list_all_questions(db: Session):
    """返回全站共享题库的所有题目查询（全站只有一个共享题库，不按课程过滤）。"""
    return _active_questions_query(db)


def count_all_questions(db: Session) -> int:
    """统计全站共享题库的题目总数。"""
    return _active_questions_query(db).count()


def _candidate_stem_fragment(stem: str) -> str:
    """从题干抽取用于 ilike 过滤的候选片段。

    使用题干归约后的第一个词（如果首词足够长）或前 30 个字符，
    缩小查重时的数据库扫描范围。
    """
    normalized = normalize_question_stem(stem)
    first_token = re.split(r"\s+", normalized, maxsplit=1)[0]
    if len(first_token) >= 4:
        return first_token[:30]
    return normalized[:30]


def find_duplicate_question(
    db: Session,
    question_type: str,
    stem: str,
    options,
    answer: str,
    exclude_question_id: int | None = None,
) -> Question | None:
    """在全站共享题库中查找重复题目（不区分课程，全站一套题）。

    先用题型和题干候选片段缩小候选集，再对候选集做完整指纹比对，
    减少进入 Python 层全量比对的风险。
    """
    fingerprint = build_question_fingerprint(question_type, stem, options, answer)
    fragment = _candidate_stem_fragment(stem)
    query = _active_questions_query(db).filter(Question.type == question_type)
    if fragment:
        query = query.filter(Question.stem.ilike(f"%{fragment}%"))
    if exclude_question_id is not None:
        query = query.filter(Question.id != exclude_question_id)
    for question in query.all():
        if build_question_fingerprint_from_question(question) == fingerprint:
            return question
    return None
