"""课程接口响应组装。"""
from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.timezone_utils import to_beijing_iso
from app.models.entities import Class, Course, CourseStage, Material, Question, StudentClassEnrollment
from app.schemas.common import AuthUser
from app.services.material_service import format_material_preview
from app.services.question_service import list_courses


def _format_course(
    db: Session,
    course: Course,
    current_user: AuthUser,
    class_count: int | None = None,
    material_count: int | None = None,
    question_count: int | None = None,
) -> dict:
    if class_count is None:
        class_count = (
            db.query(func.count(Class.id))
            .filter(Class.course_id == course.id, Class.created_by == current_user.id, Class.deleted_at.is_(None))
            .scalar()
            if current_user.role == "teacher"
            else 0
        ) or 0
    if material_count is None:
        material_count = (
            db.query(func.count(Material.id))
            .filter(Material.course_id == course.id, Material.deleted_at.is_(None))
            .scalar()
        ) or 0
    if question_count is None:
        # 全站共享题库：题目数为全站题目总数
        question_count = db.query(func.count(Question.id)).filter(Question.deleted_at.is_(None)).scalar() or 0
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description or "",
        "created_at": to_beijing_iso(course.created_at),
        "created_by": course.created_by,
        "is_public": bool(course.is_public),
        "is_owner": course.created_by == current_user.id,
        "material_count": material_count,
        "question_count": question_count,
        "class_count": class_count,
    }


def _count_by_course(rows) -> dict[int, int]:
    """把 (course_id, total) 二元组列表转成 {course_id: total} 字典。"""
    return {int(course_id): int(total or 0) for course_id, total in rows}


def _format_course_batch(db: Session, courses: list[Course], current_user: AuthUser) -> list[dict]:
    """批量格式化课程，预计算资料数、班级数和题目总数，避免逐课程 N+1 查询。"""
    course_ids = [course.id for course in courses]
    # 全站共享题库：题目数为全站题目总数，与单条格式化保持一致
    question_count = db.query(func.count(Question.id)).filter(Question.deleted_at.is_(None)).scalar() or 0
    if not course_ids:
        return []
    material_counts = _count_by_course(
        db.query(Material.course_id, func.count(Material.id))
        .filter(
            Material.course_id.in_(course_ids),
            Material.deleted_at.is_(None),
        )
        .group_by(Material.course_id)
        .all()
    )
    class_query = (
        db.query(Class.course_id, func.count(Class.id))
        .filter(
            Class.course_id.in_(course_ids),
            Class.deleted_at.is_(None),
        )
    )
    if current_user.role == "teacher":
        class_query = class_query.filter(Class.created_by == current_user.id)
    class_counts = _count_by_course(class_query.group_by(Class.course_id).all())
    return [
        _format_course(
            db,
            course,
            current_user,
            class_count=class_counts.get(course.id, 0),
            material_count=material_counts.get(course.id, 0),
            question_count=question_count,
        )
        for course in courses
    ]


def build_course_page(
    db: Session,
    current_user: AuthUser,
    keyword: str | None = None,
    scope: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int, int, int]:
    """课程列表数据库分页：在数据库层完成过滤、计数和 limit/offset。"""
    safe_page = max(page or 1, 1)
    safe_page_size = max(min(page_size or 20, 100), 1)
    query = db.query(Course).filter(Course.deleted_at.is_(None))

    if current_user.role == "teacher":
        if scope == "owned":
            query = query.filter(Course.created_by == current_user.id)
        elif scope == "public":
            query = query.filter(Course.is_public.is_(True), Course.created_by != current_user.id)
        else:
            query = query.filter(or_(Course.created_by == current_user.id, Course.is_public.is_(True)))
    elif current_user.role == "student":
        enrolled_course_ids = (
            db.query(Class.course_id)
            .join(StudentClassEnrollment, StudentClassEnrollment.class_id == Class.id)
            .filter(StudentClassEnrollment.user_id == current_user.id, Class.course_id.isnot(None), Class.deleted_at.is_(None))
            .distinct()
        )
        query = query.filter(Course.id.in_(enrolled_course_ids))

    if keyword:
        query = query.filter(Course.name.ilike(f"%{keyword.strip()}%"))

    total = query.count()
    courses = (
        query.order_by(Course.is_public.asc(), Course.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return _format_course_batch(db, courses, current_user), total, safe_page, safe_page_size


def build_course_list(db: Session, current_user: AuthUser, keyword: str | None = None):
    if current_user.role == "teacher":
        courses = list_courses(db, current_user.id, keyword)
        return _format_course_batch(db, courses, current_user)

    if current_user.role == "student":
        enrollments = (
            db.query(StudentClassEnrollment)
            .filter(StudentClassEnrollment.user_id == current_user.id)
            .all()
        )
        if not enrollments:
            return {
                "courses": [],
                "hint": "你尚未加入任何班级，请联系老师",
            }

        class_ids = [item.class_id for item in enrollments]
        classes_with_course = (
            db.query(Class)
            .filter(Class.id.in_(class_ids), Class.course_id.isnot(None), Class.deleted_at.is_(None))
            .all()
        )
        enrolled_course_ids = list({item.course_id for item in classes_with_course})
        if not enrolled_course_ids:
            return {
                "courses": [],
                "hint": "你所在班级尚未关联课程，请联系老师",
            }

        # 学生端课程入口只展示学生已加入班级对应的课程，公共课程模板不直接铺给学生。
        query = db.query(Course).filter(Course.id.in_(enrolled_course_ids), Course.deleted_at.is_(None))
        if keyword:
            query = query.filter(Course.name.ilike(f"%{keyword.strip()}%"))
        courses = query.order_by(Course.id.desc()).all()
        return {
            "courses": _format_course_batch(db, courses, current_user),
            "hint": None if courses else "未找到匹配的课程",
        }

    courses = list_courses(db, keyword=keyword)
    return _format_course_batch(db, courses, current_user)


def _format_material(material):
    return {
        "id": material.id,
        "course_id": material.course_id,
        "course_name": material.course.name if material.course else "",
        "type": material.type,
        "title": material.title,
        "url": material.url,
        "duration": material.duration,
        "pages": material.pages,
        "size": material.size,
        "date": material.date,
        "file_id": material.file_id,
        "source_material_id": material.source_material_id,
        "is_synced": bool(material.source_material_id),
        "stage_id": material.stage_id,
        "preview": format_material_preview(material.preview),
    }


def build_course_detail(db: Session, detail: tuple[Course, int, int, int], current_user: AuthUser) -> dict:
    course, material_count, question_count, class_count = detail
    visible_class_count = (
        db.query(Class).filter(Class.course_id == course.id, Class.created_by == current_user.id, Class.deleted_at.is_(None)).count()
        if current_user.role == "teacher"
        else class_count
    )
    data = _format_course(db, course, current_user, visible_class_count)
    data["material_count"] = material_count
    data["question_count"] = question_count

    stages = []
    for stage in sorted(course.stages, key=lambda s: (s.sort_order, s.id)):
        stage_data = {
            "id": stage.id,
            "course_id": stage.course_id,
            "source_stage_id": stage.source_stage_id,
            "name": stage.name,
            "sort_order": stage.sort_order,
            "created_at": to_beijing_iso(stage.created_at),
            "materials": [_format_material(m) for m in stage.materials],
        }
        stages.append(stage_data)
    data["stages"] = stages

    uncategorized = [_format_material(m) for m in course.materials if m.stage_id is None]
    data["uncategorized_materials"] = uncategorized

    return data
