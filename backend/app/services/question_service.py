"""Question service"""
from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Chapter, Course, Material, Question, StudentProgress


def list_questions(db: Session, chapter_id: int = None, type_: str = None, course_id: int = None):
    # 始终 JOIN Chapter，支持 course 维度筛选及读取课程信息
    query = db.query(Question).join(Chapter)
    if course_id is not None:
        query = query.filter(Chapter.course_id == course_id)
    if chapter_id is not None:
        query = query.filter(Question.chapter_id == chapter_id)
    if type_ is not None:
        query = query.filter(Question.type == type_)
    return query.order_by(Question.id).all()


def get_question(db: Session, question_id: int):
    return db.query(Question).filter(Question.id == question_id).first()


def create_question(db: Session, data: dict):
    q = Question(**data)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def update_question(db: Session, question_id: int, data: dict):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        return None
    for key, value in data.items():
        if value is not None and hasattr(q, key):
            setattr(q, key, value)
    db.commit()
    return q


def delete_question(db: Session, question_id: int):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        return False
    db.delete(q)
    db.commit()
    return True


def get_chapter_questions(db: Session, chapter_id: int):
    return db.query(Question).filter(Question.chapter_id == chapter_id).order_by(Question.id).all()


def list_courses(db: Session):
    return db.query(Course).order_by(Course.id.desc()).all()


def create_course(db: Session, name: str):
    if db.query(Course).filter(Course.name == name).first():
        raise BusinessException(400, "课程已存在")
    course = Course(name=name)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course_id: int, name: str):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return None
    if name != course.name:
        duplicate = db.query(Course).filter(
            Course.name == name, Course.id != course_id).first()
        if duplicate:
            raise BusinessException(400, "课程已存在")
    course.name = name
    db.commit()
    return course


def delete_course(db: Session, course_id: int):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return None
    chapter_ids = [item.id for item in db.query(
        Chapter.id).filter(Chapter.course_id == course_id).all()]
    if chapter_ids:
        has_materials = db.query(Material).filter(
            Material.chapter_id.in_(chapter_ids)).count() > 0
        has_questions = db.query(Question).filter(
            Question.chapter_id.in_(chapter_ids)).count() > 0
        has_progress = db.query(StudentProgress).filter(
            StudentProgress.chapter_id.in_(chapter_ids)).count() > 0
        if has_materials or has_questions or has_progress:
            raise BusinessException(400, "课程下仍有章节关联资料、题目或学习记录，不能直接删除")
    db.delete(course)
    db.commit()
    return True


def get_course_detail(db: Session, course_id: int):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return None
    chapters = (
        db.query(Chapter)
        .filter(Chapter.course_id == course_id)
        .order_by(Chapter.sort_order, Chapter.id)
        .all()
    )
    material_count = (
        db.query(Material)
        .join(Chapter, Material.chapter_id == Chapter.id)
        .filter(Chapter.course_id == course_id)
        .count()
    )
    return course, chapters, material_count


def import_questions_from_excel(db: Session, rows: list[dict]):
    success_count = 0
    fail_count = 0
    errors = []
    for idx, row in enumerate(rows, start=2):
        try:
            chapter_key = str(row.get("chapter", "")).strip()
            ch = db.query(Chapter).filter((Chapter.num == chapter_key) | (
                Chapter.title == chapter_key)).first()
            if not ch:
                raise BusinessException(400, f"未找到章节: {chapter_key}")
            q_type = str(row.get("type", "")).strip()
            stem = str(row.get("stem", "")).strip()
            if not stem:
                raise BusinessException(400, "题干为空")
            options = str(row.get("options", "")).strip()
            option_list = [x.strip() for x in options.split("|")
                           if x.strip()] if options else []
            answer = str(row.get("answer", "")).strip()
            explanation = str(row.get("explanation", "")).strip()
            q = Question(type=q_type, chapter_id=ch.id, stem=stem,
                         options=option_list, answer=answer, explanation=explanation)
            db.add(q)
            success_count += 1
        except Exception as exc:
            fail_count += 1
            errors.append({"row": idx, "reason": str(exc)})
    db.commit()
    return {"success_count": success_count, "fail_count": fail_count, "errors": errors}
