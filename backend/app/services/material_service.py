"""资料服务。"""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Class, Course, Material, StudentClassEnrollment


def list_materials(
    db: Session,
    course_id: int | None = None,
    teacher_id: str | None = None,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    include_public_sources: bool = True,
):
    query = db.query(Material).join(Course, Course.id == Material.course_id)
    if teacher_id is not None:
        if include_public_sources:
            query = query.filter(
                or_(Course.created_by == teacher_id, Course.is_public.is_(True)))
        else:
            query = query.filter(Course.created_by == teacher_id)
    if course_id is not None:
        query = query.filter(Material.course_id == course_id)
    if keyword:
        query = query.filter(Material.title.contains(keyword))
    total = query.count()
    if page and page_size:
        materials = query.order_by(Material.course_id, Material.id).offset((page - 1) * page_size).limit(page_size).all()
    else:
        materials = query.order_by(Material.course_id, Material.id).all()
    return materials, total


def can_view_course_materials(db: Session, course_id: int, user_id: str, role: str) -> bool:
    """校验课程资料访问权限：学生限所在课程，教师限自有或公共课程。"""
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
            or_(Course.created_by == user_id, Course.is_public.is_(True)),
        ).first() is not None
    return db.query(Course).filter(Course.id == course_id).first() is not None


def create_material(
    db: Session,
    course_id: int,
    type_: str,
    title: str,
    url: str = "",
    size: str = "0 MB",
    file_id: int | None = None,
    teacher_id: str | None = None,
):
    query = db.query(Course).filter(Course.id == course_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    course = query.first()
    if not course:
        return None
    material = Material(
        course_id=course_id,
        type=type_,
        title=title,
        url=url,
        size=size,
        date=datetime.now().strftime("%Y-%m-%d"),
        file_id=file_id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def delete_material(db: Session, material_id: int, teacher_id: str | None = None):
    query = db.query(Material).join(Course, Course.id == Material.course_id).filter(Material.id == material_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    m = query.first()
    if not m:
        return False
    if m.source_material_id is not None:
        raise BusinessException(400, "公共课程同步内容不能删除")
    db.delete(m)
    db.commit()
    return True
