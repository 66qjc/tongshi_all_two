"""Chapter service"""
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Chapter, Course, Material, Question, QuizAttempt, StudentProgress


def list_chapters(db: Session, user_id: str = None):
    chapters = db.query(Chapter).order_by(Chapter.sort_order).all()
    return format_chapters(db, chapters, user_id)


def format_chapters(db: Session, chapters: list[Chapter], user_id: str = None):
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
            "sort_order": ch.sort_order or 0,
            "videos": videos,
            "docs": docs,
            "progress": progress,
            "course_id": ch.course_id,
            "course_name": ch.course.name if ch.course else "",
            "day_of_week": ch.day_of_week or "",
            "class_periods": ch.class_periods or "",
            "schedule_note": ch.schedule_note or "",
        })
    return result


def get_chapter(db: Session, chapter_num: str):
    return db.query(Chapter).filter(Chapter.num == chapter_num).first()


def create_chapter(db: Session, data: dict):
    if db.query(Chapter).filter(Chapter.num == data["num"]).first():
        raise BusinessException(400, "章节编号已存在")
    course_id = data.get("course_id")
    if course_id and not db.query(Course).filter(Course.id == course_id).first():
        raise BusinessException(404, "课程不存在")
    chapter = Chapter(**data)
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


def update_chapter(db: Session, chapter_id: int, data: dict):
    ch = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not ch:
        return None
    if "num" in data and data["num"] and data["num"] != ch.num:
        duplicate = db.query(Chapter).filter(Chapter.num == data["num"], Chapter.id != chapter_id).first()
        if duplicate:
            raise BusinessException(400, "章节编号已存在")
    if "course_id" in data and data["course_id"]:
        if not db.query(Course).filter(Course.id == data["course_id"]).first():
            raise BusinessException(404, "课程不存在")
    for key, value in data.items():
        if hasattr(ch, key):
            setattr(ch, key, value)
    db.commit()
    return ch


def delete_chapter(db: Session, chapter_id: int):
    ch = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not ch:
        return False
    question_ids = [item.id for item in db.query(Question.id).filter(Question.chapter_id == chapter_id).all()]
    if question_ids:
        db.query(QuizAttempt).filter(QuizAttempt.question_id.in_(question_ids)).delete(synchronize_session=False)
    db.query(StudentProgress).filter(StudentProgress.chapter_id == chapter_id).delete(synchronize_session=False)
    db.query(Material).filter(Material.chapter_id == chapter_id).delete(synchronize_session=False)
    db.query(Question).filter(Question.chapter_id == chapter_id).delete(synchronize_session=False)
    db.delete(ch)
    db.commit()
    return True
