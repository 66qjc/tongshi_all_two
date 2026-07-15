"""公开学习馆只读服务。"""
from __future__ import annotations

from urllib.parse import quote

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.timezone_utils import to_beijing_iso
from app.models.entities import Course, CourseStage, Lesson, Material, StoredFile
from app.services.file_service import build_x_accel_redirect_path
from app.services.lesson_service import format_lesson_out
from app.services.material_service import format_material_preview


def _format_public_material(material: Material) -> dict:
    """格式化公开资料输出。"""
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


def _count_by_course(rows) -> dict[int, int]:
    """将分组统计结果转换为课程 ID 到数量的映射。"""
    return {int(course_id): int(total or 0) for course_id, total in rows}


def _public_course_query(db: Session):
    """公开课程基础查询（排除软删）。"""
    return db.query(Course).filter(
        Course.is_public.is_(True),
        Course.deleted_at.is_(None),
    )


def _format_public_course(
    course: Course,
    lesson_count: int = 0,
    material_count: int = 0,
) -> dict:
    """格式化公开课程输出，游客视角下无归属权限。"""
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description or "",
        "created_at": to_beijing_iso(course.created_at),
        "created_by": course.created_by,
        "is_public": True,
        "is_owner": False,
        "material_count": material_count,
        "lesson_count": lesson_count,
        "question_count": 0,
        "class_count": 0,
    }


def list_public_courses(db: Session, keyword: str | None = None) -> dict:
    """游客读取公开课程列表。"""
    query = _public_course_query(db)
    if keyword:
        query = query.filter(Course.name.ilike(f"%{keyword.strip()}%"))
    courses = query.order_by(Course.id.desc()).all()
    course_ids = [course.id for course in courses]
    if not course_ids:
        return {"courses": [], "hint": "暂无公开课程"}

    lesson_counts = _count_by_course(
        db.query(Lesson.course_id, func.count(Lesson.id))
        .filter(Lesson.course_id.in_(course_ids), Lesson.status == "published")
        .group_by(Lesson.course_id)
        .all()
    )
    material_counts = _count_by_course(
        db.query(Material.course_id, func.count(Material.id))
        .filter(
            Material.course_id.in_(course_ids),
            Material.deleted_at.is_(None),
        )
        .group_by(Material.course_id)
        .all()
    )
    return {
        "courses": [
            _format_public_course(
                course,
                lesson_count=lesson_counts.get(course.id, 0),
                material_count=material_counts.get(course.id, 0),
            )
            for course in courses
        ],
        "hint": None,
    }


def get_public_course(db: Session, course_id: int) -> Course:
    """获取公开课程对象，非公开课程视为不存在。"""
    course = _public_course_query(db).filter(Course.id == course_id).first()
    if not course:
        raise BusinessException(404, "课程不存在")
    return course


def build_public_course_detail(db: Session, course_id: int) -> dict:
    """构建公开课程详情，包含阶段和资料。"""
    course = get_public_course(db, course_id)
    lesson_count = (
        db.query(func.count(Lesson.id))
        .filter(Lesson.course_id == course.id, Lesson.status == "published")
        .scalar()
        or 0
    )
    material_count = (
        db.query(func.count(Material.id))
        .filter(Material.course_id == course.id, Material.deleted_at.is_(None))
        .scalar()
        or 0
    )
    data = _format_public_course(course, lesson_count=lesson_count, material_count=material_count)

    stages = []
    for stage in sorted(course.stages, key=lambda item: (item.sort_order, item.id)):
        stage_data = {
            "id": stage.id,
            "course_id": stage.course_id,
            "source_stage_id": stage.source_stage_id,
            "name": stage.name,
            "sort_order": stage.sort_order,
            "created_at": to_beijing_iso(stage.created_at),
            "materials": [
                _format_public_material(material)
                for material in stage.materials
                if getattr(material, "deleted_at", None) is None
            ],
        }
        stages.append(stage_data)
    data["stages"] = stages
    data["uncategorized_materials"] = [
        _format_public_material(material)
        for material in course.materials
        if material.stage_id is None and getattr(material, "deleted_at", None) is None
    ]
    return data


def list_public_lessons(db: Session, course_id: int) -> list[dict]:
    """游客读取公开课程下已发布课时。"""
    get_public_course(db, course_id)
    lessons = (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id, Lesson.status == "published")
        .order_by(Lesson.sort_order, Lesson.id)
        .all()
    )
    return [format_lesson_out(lesson) for lesson in lessons]


def list_public_materials(
    db: Session,
    course_id: int | None = None,
    keyword: str | None = None,
    limit: int = 12,
) -> dict:
    """游客读取公开课程资料列表。"""
    safe_limit = max(1, min(limit or 12, 50))
    query = (
        db.query(Material)
        .join(Course, Course.id == Material.course_id)
        .filter(
            Course.is_public.is_(True),
            Course.deleted_at.is_(None),
            Material.deleted_at.is_(None),
        )
    )
    if course_id is not None:
        query = query.filter(Material.course_id == course_id)
    if keyword:
        query = query.filter(Material.title.ilike(f"%{keyword.strip()}%"))
    total = query.count()
    materials = query.order_by(Material.id.desc()).limit(safe_limit).all()
    return {"items": [_format_public_material(material) for material in materials], "total": total}


def resolve_public_material_file(db: Session, material_id: int):
    """校验公开资料文件权限并返回 Nginx 内部跳转所需信息。"""
    material = (
        db.query(Material)
        .join(Course, Course.id == Material.course_id)
        .filter(
            Material.id == material_id,
            Course.is_public.is_(True),
            Course.deleted_at.is_(None),
            Material.deleted_at.is_(None),
        )
        .first()
    )
    if not material:
        raise BusinessException(404, "资料不存在")
    if not material.file_id:
        raise BusinessException(404, "资料文件不存在")

    stored = db.query(StoredFile).filter(StoredFile.id == material.file_id).first()
    if not stored:
        raise BusinessException(404, "资料文件不存在")
    if stored.storage_provider != "local":
        raise BusinessException(400, "当前试点仅支持本地文件预览")
    try:
        accel_path = build_x_accel_redirect_path(stored.object_key)
    except ValueError:
        raise BusinessException(400, "资料文件路径不合法")

    filename = stored.original_name or stored.stored_name or material.title or "material"
    encoded = quote(filename, encoding="utf-8")
    headers = {
        "X-Accel-Redirect": accel_path,
        "Content-Disposition": f"inline; filename*=UTF-8''{encoded}",
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=300",
    }
    return material, stored, headers
