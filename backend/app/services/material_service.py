"""Material service"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.entities import Material, Chapter


def list_materials(db: Session, chapter_id: int = None):
    query = db.query(Material)
    if chapter_id:
        query = query.filter(Material.chapter_id == chapter_id)
    return query.order_by(Material.id).all()


def list_all_materials(db: Session):
    return db.query(Material).join(Chapter).order_by(Material.chapter_id, Material.id).all()


def create_material(db: Session, chapter_id: int, type_: str, title: str, url: str = "", size: str = "0 MB"):
    ch = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not ch:
        return None
    material = Material(
        chapter_id=chapter_id,
        type=type_,
        title=title,
        url=url,
        size=size,
        date=datetime.now().strftime("%Y-%m-%d"),
    )
    db.add(material)
    db.commit()
    return material


def delete_material(db: Session, material_id: int):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        return False
    db.delete(m)
    db.commit()
    return True
