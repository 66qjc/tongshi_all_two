"""题库与课程服务。"""
from __future__ import annotations

import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Class, Course, Material, Question, StudentClassEnrollment
from app.services.public_course_sync_service import mirror_public_course_content


def list_questions(
    db: Session,
    course_id: int | None = None,
    type_: str | None = None,
    teacher_id: str | None = None,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
):
    query = db.query(Question).join(Course, Course.id == Question.course_id)
    if teacher_id is not None:
        query = query.filter(_course_access_filter(teacher_id))
    if course_id is not None:
        query = query.filter(Question.course_id == course_id)
    if type_ is not None:
        query = query.filter(Question.type == type_)
    if keyword:
        query = query.filter(Question.stem.contains(keyword))
    total = query.count()
    if page and page_size:
        questions = query.order_by(Question.id).offset((page - 1) * page_size).limit(page_size).all()
    else:
        questions = query.order_by(Question.id).all()
    return questions, total


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


def get_question(db: Session, question_id: int, teacher_id: str | None = None):
    query = db.query(Question).join(Course, Course.id == Question.course_id).filter(Question.id == question_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    return query.first()


def _get_owned_course(db: Session, course_id: int, teacher_id: str):
    return db.query(Course).filter(Course.id == course_id, Course.created_by == teacher_id).first()


def _course_access_filter(teacher_id: str):
    return or_(Course.created_by == teacher_id, Course.is_public.is_(True))


def create_question(db: Session, data: dict, teacher_id: str):
    if not _get_owned_course(db, data["course_id"], teacher_id):
        raise BusinessException(404, "课程不存在")
    data["tags"] = _normalize_tags(data.get("tags"))
    q = Question(**data)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def update_question(db: Session, question_id: int, data: dict, teacher_id: str):
    q = get_question(db, question_id, teacher_id)
    if not q:
        return None
    if q.source_question_id is not None:
        raise BusinessException(400, "公共课程同步内容不能修改")
    if "course_id" in data and data["course_id"] is not None:
        if not _get_owned_course(db, data["course_id"], teacher_id):
            raise BusinessException(404, "课程不存在")
    for key, value in data.items():
        if value is not None and hasattr(q, key):
            setattr(q, key, _normalize_tags(value) if key == "tags" else value)
    db.commit()
    return q


def delete_question(db: Session, question_id: int, teacher_id: str):
    q = get_question(db, question_id, teacher_id)
    if not q:
        return False
    if q.source_question_id is not None:
        raise BusinessException(400, "公共课程同步内容不能删除")
    # 先删除关联的答题记录
    from app.models.entities import QuizAttempt, Announcement
    from sqlalchemy import func as sa_func
    db.query(QuizAttempt).filter(QuizAttempt.question_id == question_id).delete()
    # 清理公告中对被删题目的引用（从 question_ids JSON 数组中移除该 ID）
    anns = db.query(Announcement).filter(
        sa_func.json_contains(Announcement.question_ids, str(question_id))
    ).all()
    for ann in anns:
        if ann.question_ids:
            ann.question_ids = [qid for qid in ann.question_ids if qid != question_id]
    # 再删除题目
    db.delete(q)
    db.commit()
    return True


def get_course_questions(db: Session, course_id: int):
    return db.query(Question).filter(Question.course_id == course_id).order_by(Question.id).all()


def can_view_course_questions(db: Session, course_id: int, user_id: str, role: str) -> bool:
    """校验课程题目访问权限：学生限所在课程，教师限自有或公共课程。"""
    if role == "student":
        return db.query(StudentClassEnrollment).join(
            Class, Class.id == StudentClassEnrollment.class_id,
        ).filter(
            StudentClassEnrollment.user_id == user_id,
            Class.course_id == course_id,
        ).first() is not None
    if role == "teacher":
        return db.query(Course).filter(
            Course.id == course_id,
            _course_access_filter(user_id),
        ).first() is not None
    return db.query(Course).filter(Course.id == course_id).first() is not None


def list_courses(db: Session, teacher_id: str | None = None, keyword: str | None = None):
    query = db.query(Course)
    if teacher_id is not None:
        query = query.filter(_course_access_filter(teacher_id))
    if keyword:
        query = query.filter(Course.name.contains(keyword))
    return query.order_by(Course.is_public.asc(), Course.id.desc()).all()


def create_course(db: Session, name: str, teacher_id: str, is_public: bool = False):
    if db.query(Course).filter(Course.name == name, Course.created_by == teacher_id).first():
        raise BusinessException(400, "课程已存在")
    course = Course(name=name, created_by=teacher_id, is_public=is_public)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def add_public_course(db: Session, course_id: int, teacher_id: str):
    source = db.query(Course).filter(
        Course.id == course_id,
        Course.is_public.is_(True),
    ).first()
    if not source:
        raise BusinessException(404, "公共课程不存在")

    existing = db.query(Course).filter(Course.name == source.name, Course.created_by == teacher_id).first()
    if existing:
        return existing

    course = Course(name=source.name, created_by=teacher_id,
                    is_public=False, source_course_id=source.id)
    db.add(course)
    db.flush()

    mirror_public_course_content(db, source, course)

    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course_id: int, name: str, teacher_id: str, is_public: bool | None = None):
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
    if is_public is not None:
        course.is_public = is_public
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
        query = query.filter(_course_access_filter(teacher_id))
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
            course_name = str(_row_value(row, "课程名称", "课程", "course", "course_name")).strip()
            course = db.query(Course).filter(
                Course.name == course_name,
                Course.created_by == teacher_id,
            ).first()
            if not course:
                raise BusinessException(400, f"未找到课程: {course_name}")
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
            q = Question(type=q_type, course_id=course.id, stem=stem,
                         options=option_list, answer=answer, explanation=explanation, tags=tags)
            db.add(q)
            success_count += 1
        except Exception as exc:
            fail_count += 1
            errors.append({"row": idx, "reason": str(exc)})
    db.commit()
    return {"success_count": success_count, "fail_count": fail_count, "errors": errors}
