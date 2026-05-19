"""Question service"""
from sqlalchemy.orm import Session
from app.models.entities import Question


def list_questions(db: Session, chapter_id: int = None, type_: str = None):
    query = db.query(Question)
    if chapter_id:
        query = query.filter(Question.chapter_id == chapter_id)
    if type_:
        query = query.filter(Question.type == type_)
    return query.order_by(Question.id).all()


def get_question(db: Session, question_id: int):
    return db.query(Question).filter(Question.id == question_id).first()


def create_question(db: Session, data: dict):
    q = Question(**data)
    db.add(q)
    db.commit()
    return q


def update_question(db: Session, question_id: int, data: dict):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        return None
    for key, value in data.items():
        if value is not None and hasattr(q, key):
            setattr(q, key, value)
    db.commit()
    return q


def delete_question(db: Session, question_id: int):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        return False
    db.delete(q)
    db.commit()
    return True


def get_chapter_questions(db: Session, chapter_id: int):
    return db.query(Question).filter(Question.chapter_id == chapter_id).order_by(Question.id).all()
