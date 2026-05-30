"""题库与课程服务。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Class, Course, Material, Question, StudentProgress


def list_questions(
    db: Session,
    course_id: int | None = None,
    type_: str | None = None,
    teacher_id: str | None = None,
):
    query = db.query(Question).join(Course, Course.id == Question.course_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    if course_id is not None:
        query = query.filter(Question.course_id == course_id)
    if type_ is not None:
        query = query.filter(Question.type == type_)
    return query.order_by(Question.id).all()


def get_question(db: Session, question_id: int, teacher_id: str | None = None):
    query = db.query(Question).join(Course, Course.id == Question.course_id).filter(Question.id == question_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    return query.first()


def _get_owned_course(db: Session, course_id: int, teacher_id: str):
    return db.query(Course).filter(Course.id == course_id, Course.created_by == teacher_id).first()


def create_question(db: Session, data: dict, teacher_id: str):
    if not _get_owned_course(db, data["course_id"], teacher_id):
        raise BusinessException(404, "课程不存在")
    q = Question(**data)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def update_question(db: Session, question_id: int, data: dict, teacher_id: str):
    q = get_question(db, question_id, teacher_id)
    if not q:
        return None
    if "course_id" in data and data["course_id"] is not None:
        if not _get_owned_course(db, data["course_id"], teacher_id):
            raise BusinessException(404, "课程不存在")
    for key, value in data.items():
        if value is not None and hasattr(q, key):
            setattr(q, key, value)
    db.commit()
    return q


def delete_question(db: Session, question_id: int, teacher_id: str):
    q = get_question(db, question_id, teacher_id)
    if not q:
        return False
    db.delete(q)
    db.commit()
    return True


def get_course_questions(db: Session, course_id: int):
    return db.query(Question).filter(Question.course_id == course_id).order_by(Question.id).all()


def list_courses(db: Session, teacher_id: str | None = None):
    query = db.query(Course)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    return query.order_by(Course.id.desc()).all()


def create_course(db: Session, name: str, teacher_id: str):
    if db.query(Course).filter(Course.name == name, Course.created_by == teacher_id).first():
        raise BusinessException(400, "课程已存在")
    course = Course(name=name, created_by=teacher_id)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course_id: int, name: str, teacher_id: str):
    course = _get_owned_course(db, course_id, teacher_id)
    if not course:
        return None
    if name != course.name:
        duplicate = db.query(Course).filter(
            Course.name == name,
            Course.created_by == teacher_id,
            Course.id != course_id,
        ).first()
        if duplicate:
            raise BusinessException(400, "课程已存在")
    course.name = name
    db.commit()
    return course


def delete_course(db: Session, course_id: int, teacher_id: str):
    course = _get_owned_course(db, course_id, teacher_id)
    if not course:
        return None
    blockers = []
    if db.query(Material).filter(Material.course_id == course_id).count() > 0:
        blockers.append("资料")
    if db.query(Question).filter(Question.course_id == course_id).count() > 0:
        blockers.append("题目")
    if db.query(StudentProgress).filter(StudentProgress.course_id == course_id).count() > 0:
        blockers.append("学习记录")
    if db.query(Class).filter(Class.course_id == course_id).count() > 0:
        blockers.append("班级")
    if blockers:
        raise BusinessException(400, f"课程下仍有{'、'.join(blockers)}，不能直接删除")
    db.delete(course)
    db.commit()
    return True


def get_course_detail(db: Session, course_id: int, teacher_id: str | None = None):
    query = db.query(Course).filter(Course.id == course_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    course = query.first()
    if not course:
        return None
    material_count = db.query(Material).filter(Material.course_id == course_id).count()
    question_count = db.query(Question).filter(Question.course_id == course_id).count()
    class_count = db.query(Class).filter(Class.course_id == course_id).count()
    return course, material_count, question_count, class_count


def import_questions_from_excel(db: Session, rows: list[dict], teacher_id: str):
    success_count = 0
    fail_count = 0
    errors = []
    for idx, row in enumerate(rows, start=2):
        try:
            course_name = str(row.get("course", "")).strip()
            course = db.query(Course).filter(
                Course.name == course_name,
                Course.created_by == teacher_id,
            ).first()
            if not course:
                raise BusinessException(400, f"未找到课程: {course_name}")
            q_type = str(row.get("type", "")).strip()
            stem = str(row.get("stem", "")).strip()
            if not stem:
                raise BusinessException(400, "题干为空")
            options = str(row.get("options", "")).strip()
            option_list = [x.strip() for x in options.split("|")
                           if x.strip()] if options else []
            answer = str(row.get("answer", "")).strip()
            explanation = str(row.get("explanation", "")).strip()
            q = Question(type=q_type, course_id=course.id, stem=stem,
                         options=option_list, answer=answer, explanation=explanation)
            db.add(q)
            success_count += 1
        except Exception as exc:
            fail_count += 1
            errors.append({"row": idx, "reason": str(exc)})
    db.commit()
    return {"success_count": success_count, "fail_count": fail_count, "errors": errors}
