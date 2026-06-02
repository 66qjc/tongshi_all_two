"""资料服务。"""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entities import Course, Material


def list_materials(db: Session, course_id: int | None = None, teacher_id: str | None = None):
    query = db.query(Material).join(Course, Course.id == Material.course_id)
    if teacher_id is not None:
        query = query.filter(
            or_(Course.created_by == teacher_id, Course.is_public.is_(True)))
    if course_id is not None:
        query = query.filter(Material.course_id == course_id)
    return query.order_by(Material.course_id, Material.id).all()


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
    db.delete(m)
    db.commit()
    return True
