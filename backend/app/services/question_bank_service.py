"""共享题库辅助函数。"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.entities import Course, Question


def resolve_question_bank_course(db: Session, course: Course) -> Course:
    """解析课程所属的共享题库根课程。"""
    if course.question_bank_root_course_id is None:
        return course
    root = db.query(Course).filter(Course.id == course.question_bank_root_course_id).first()
    return root or course


def get_shared_question_bank_root_course(db: Session) -> Course | None:
    """获取当前系统内的共享题库根课程。"""
    root = db.query(Course).filter(
        Course.question_bank_root_course_id.is_(None),
    ).order_by(
        Course.is_public.desc(),
        Course.id.asc(),
    ).first()
    if root:
        return root

    referenced_root_id = db.query(Course.question_bank_root_course_id).filter(
        Course.question_bank_root_course_id.isnot(None),
    ).order_by(Course.id.asc()).first()
    if referenced_root_id and referenced_root_id[0] is not None:
        return db.query(Course).filter(Course.id == referenced_root_id[0]).first()
    return None


def get_question_bank_course(db: Session, course: Course | None) -> Course | None:
    if course is None:
        return get_shared_question_bank_root_course(db)
    return resolve_question_bank_course(db, course)


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
    for question in db.query(Question).all():
        fingerprints.add(build_question_fingerprint_from_question(question))
    return fingerprints


def list_all_questions(db: Session):
    """返回全站共享题库的所有题目查询（全站只有一个共享题库，不按课程过滤）。"""
    return db.query(Question)


def count_all_questions(db: Session) -> int:
    """统计全站共享题库的题目总数。"""
    return db.query(Question).count()


def find_duplicate_question(
    db: Session,
    question_type: str,
    stem: str,
    options,
    answer: str,
    exclude_question_id: int | None = None,
) -> Question | None:
    """在全站共享题库中查找重复题目（不区分课程，全站一套题）。"""
    fingerprint = build_question_fingerprint(question_type, stem, options, answer)
    for question in db.query(Question).all():
        if exclude_question_id is not None and question.id == exclude_question_id:
            continue
        if build_question_fingerprint_from_question(question) == fingerprint:
            return question
    return None
