"""Chapter service"""
from sqlalchemy.orm import Session
from app.models.entities import Chapter, Material, StudentProgress


def list_chapters(db: Session, user_id: str = None):
    chapters = db.query(Chapter).order_by(Chapter.sort_order).all()
    result = []
    for ch in chapters:
        videos = db.query(Material).filter(Material.chapter_id == ch.id, Material.type == "video").count()
        docs = db.query(Material).filter(Material.chapter_id == ch.id, Material.type == "pdf").count()
        progress = 0
        if user_id:
            sp = db.query(StudentProgress).filter(
                StudentProgress.user_id == user_id,
                StudentProgress.chapter_id == ch.id,
            ).first()
            if sp:
                progress = sp.learn_progress
        result.append({
            "id": ch.id,
            "num": ch.num,
            "title": ch.title,
            "desc": ch.desc,
            "topics": ch.topics,
            "status": ch.status,
            "videos": videos,
            "docs": docs,
            "progress": progress,
        })
    return result


def get_chapter(db: Session, chapter_num: str):
    return db.query(Chapter).filter(Chapter.num == chapter_num).first()


def update_chapter(db: Session, chapter_id: int, data: dict):
    ch = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not ch:
        return None
    for key, value in data.items():
        if value is not None and hasattr(ch, key):
            setattr(ch, key, value)
    db.commit()
    return ch
