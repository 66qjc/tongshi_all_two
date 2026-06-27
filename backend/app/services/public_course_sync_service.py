"""公共课程同步服务。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import Course, CourseStage, Material, Question, QuizAttempt


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
    stage_map = {}
    for stage in source.stages:
        copy_stage = CourseStage(
            course_id=copy.id,
            source_stage_id=stage.id,
            name=stage.name,
            sort_order=stage.sort_order,
        )
        db.add(copy_stage)
        db.flush()
        stage_map[stage.id] = copy_stage

    for material in source.materials:
        copy_mat = copy_material_to_course(material, copy.id)
        if material.stage_id is not None:
            copy_stage = stage_map.get(material.stage_id)
            if copy_stage is not None:
                copy_mat.stage_id = copy_stage.id
        db.add(copy_mat)
    for question in source.questions:
        db.add(copy_question_to_course(question, copy.id))


def sync_material_to_course_copies(db: Session, source: Material) -> None:
    for course in teacher_course_copies(db, source.course_id):
        mirrored = db.query(Material).filter(
            Material.course_id == course.id,
            Material.source_material_id == source.id,
        ).first()

        target_stage_id = None
        if source.stage_id is not None:
            target_stage = db.query(CourseStage).filter(
                CourseStage.course_id == course.id,
                CourseStage.source_stage_id == source.stage_id,
            ).first()
            if target_stage is not None:
                target_stage_id = target_stage.id

        if mirrored is None:
            new_mat = copy_material_to_course(source, course.id)
            new_mat.stage_id = target_stage_id
            db.add(new_mat)
            continue
        mirrored.type = source.type
        mirrored.title = source.title
        mirrored.url = source.url
        mirrored.duration = source.duration
        mirrored.pages = source.pages
        mirrored.size = source.size
        mirrored.date = source.date
        mirrored.file_id = source.file_id
        mirrored.stage_id = target_stage_id


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


def sync_stages_to_course_copies(db: Session, source: Course) -> None:
    """将公共课程的阶段/目录元数据同步到教师副本。

    新增的阶段会复制到副本；已有的阶段（按 source_stage_id）更新名称和排序。
    不自动删除副本中已不存在的阶段，避免误删教师资料。
    """
    for course in teacher_course_copies(db, source.id):
        copy_stages = {
            s.source_stage_id: s
            for s in course.stages
            if s.source_stage_id is not None
        }
        for src_stage in source.stages:
            if src_stage.id in copy_stages:
                cs = copy_stages[src_stage.id]
                cs.name = src_stage.name
                cs.sort_order = src_stage.sort_order
            else:
                db.add(CourseStage(
                    course_id=course.id,
                    source_stage_id=src_stage.id,
                    name=src_stage.name,
                    sort_order=src_stage.sort_order,
                ))
