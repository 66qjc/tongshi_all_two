"""公共课程同步服务。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import Course, Material, Question, QuizAttempt


def teacher_course_copies(db: Session, source_course_id: int) -> list[Course]:
    """返回指定公共课程的所有教师副本。"""
    return db.query(Course).filter(Course.source_course_id == source_course_id).all()


def copy_material_to_course(source: Material, course_id: int) -> Material:
    return Material(
        course_id=course_id,
        type=source.type,
        title=source.title,
        url=source.url,
        duration=source.duration,
        pages=source.pages,
        size=source.size,
        date=source.date,
        file_id=source.file_id,
        source_material_id=source.id,
    )


def copy_question_to_course(source: Question, course_id: int) -> Question:
    return Question(
        course_id=course_id,
        type=source.type,
        stem=source.stem,
        options=list(source.options or []),
        answer=source.answer,
        explanation=source.explanation,
        tags=list(source.tags or []),
        source_question_id=source.id,
    )


def mirror_public_course_content(db: Session, source: Course, copy: Course) -> None:
    for material in source.materials:
        db.add(copy_material_to_course(material, copy.id))
    for question in source.questions:
        db.add(copy_question_to_course(question, copy.id))


def sync_material_to_course_copies(db: Session, source: Material) -> None:
    for course in teacher_course_copies(db, source.course_id):
        mirrored = db.query(Material).filter(
            Material.course_id == course.id,
            Material.source_material_id == source.id,
        ).first()
        if mirrored is None:
            db.add(copy_material_to_course(source, course.id))
            continue
        mirrored.type = source.type
        mirrored.title = source.title
        mirrored.url = source.url
        mirrored.duration = source.duration
        mirrored.pages = source.pages
        mirrored.size = source.size
        mirrored.date = source.date
        mirrored.file_id = source.file_id


def delete_synced_materials(db: Session, source_material_id: int) -> None:
    db.query(Material).filter(
        Material.source_material_id == source_material_id,
    ).delete(synchronize_session=False)


def sync_question_to_course_copies(db: Session, source: Question) -> None:
    for course in teacher_course_copies(db, source.course_id):
        mirrored = db.query(Question).filter(
            Question.course_id == course.id,
            Question.source_question_id == source.id,
        ).first()
        if mirrored is None:
            db.add(copy_question_to_course(source, course.id))
            continue
        mirrored.type = source.type
        mirrored.stem = source.stem
        mirrored.options = list(source.options or [])
        mirrored.answer = source.answer
        mirrored.explanation = source.explanation
        mirrored.tags = list(source.tags or [])


def delete_synced_questions(db: Session, source_question_id: int) -> None:
    mirrored_ids = [
        row.id
        for row in db.query(Question.id)
        .filter(Question.source_question_id == source_question_id)
        .all()
    ]
    if not mirrored_ids:
        return
    db.query(QuizAttempt).filter(
        QuizAttempt.question_id.in_(mirrored_ids),
    ).delete(synchronize_session=False)
    db.query(Question).filter(
        Question.id.in_(mirrored_ids),
    ).delete(synchronize_session=False)


def sync_course_name_to_copies(db: Session, source: Course) -> None:
    for course in teacher_course_copies(db, source.id):
        course.name = source.name
