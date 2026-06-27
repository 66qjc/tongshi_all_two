"""课程接口响应组装。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.timezone_utils import to_beijing_iso
from app.models.entities import Class, Course, CourseStage, StudentClassEnrollment
from app.schemas.common import AuthUser
from app.services.question_service import list_courses


def _format_course(db: Session, course: Course, current_user: AuthUser, class_count: int | None = None) -> dict:
    if class_count is None:
        class_count = (
            db.query(Class).filter(Class.course_id == course.id, Class.created_by == current_user.id).count()
            if current_user.role == "teacher"
            else len(course.classes)
        )
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description or "",
        "created_at": to_beijing_iso(course.created_at),
        "created_by": course.created_by,
        "is_public": bool(course.is_public),
        "is_owner": course.created_by == current_user.id,
        "material_count": len(course.materials),
        "question_count": len(course.questions),
        "class_count": class_count,
    }


def build_course_list(db: Session, current_user: AuthUser, keyword: str | None = None):
    if current_user.role == "teacher":
        courses = list_courses(db, current_user.id, keyword)
        return [_format_course(db, course, current_user) for course in courses]

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
            .filter(Class.id.in_(class_ids), Class.course_id.isnot(None))
            .all()
        )
        enrolled_course_ids = list({item.course_id for item in classes_with_course})
        if not enrolled_course_ids:
            return {
                "courses": [],
                "hint": "你所在班级尚未关联课程，请联系老师",
            }

        # 学生端课程入口只展示学生已加入班级对应的课程，公共课程模板不直接铺给学生。
        query = db.query(Course).filter(Course.id.in_(enrolled_course_ids))
        if keyword:
            query = query.filter(Course.name.contains(keyword))
        courses = query.order_by(Course.id.desc()).all()
        return {
            "courses": [_format_course(db, course, current_user) for course in courses],
            "hint": None if courses else "未找到匹配的课程",
        }

    courses = list_courses(db, keyword=keyword)
    return [_format_course(db, course, current_user) for course in courses]


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
    }


def build_course_detail(db: Session, detail: tuple[Course, int, int, int], current_user: AuthUser) -> dict:
    course, material_count, question_count, class_count = detail
    visible_class_count = (
        db.query(Class).filter(Class.course_id == course.id, Class.created_by == current_user.id).count()
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
