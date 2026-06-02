"""Teacher service"""
from sqlalchemy.orm import Session
from app.models.entities import User, Course, Project, QuizAttempt, StudentProgress, StudentClassEnrollment, Class


def _teacher_class_ids(db: Session, teacher_id: str) -> list[int]:
    return [
        row.id for row in db.query(Class.id)
        .filter(Class.created_by == teacher_id)
        .all()
    ]


def _teacher_student_ids(db: Session, teacher_id: str) -> list[str]:
    class_ids = _teacher_class_ids(db, teacher_id)
    if not class_ids:
        return []
    return [
        row.user_id for row in db.query(StudentClassEnrollment.user_id)
        .filter(StudentClassEnrollment.class_id.in_(class_ids))
        .distinct()
        .all()
    ]


def get_teacher_stats(db: Session, teacher_id: str):
    student_ids = _teacher_student_ids(db, teacher_id)
    total_students = len(student_ids)
    my_courses = db.query(Course).filter(Course.created_by == teacher_id).count()
    public_courses = db.query(Course).filter(Course.is_public.is_(True)).count()
    pending_reviews_query = db.query(Project).filter(Project.status == "pending")
    if student_ids:
        pending_reviews_query = pending_reviews_query.filter(Project.author_id.in_(student_ids))
    else:
        pending_reviews_query = pending_reviews_query.filter(False)
    pending_reviews = pending_reviews_query.count()
    weekly_exercises_query = db.query(QuizAttempt)
    if student_ids:
        weekly_exercises_query = weekly_exercises_query.filter(QuizAttempt.user_id.in_(student_ids))
    else:
        weekly_exercises_query = weekly_exercises_query.filter(False)
    weekly_exercises = weekly_exercises_query.count()  # simplified: total instead of weekly
    return {
        "total_students": total_students,
        "my_courses": my_courses,
        "public_courses": public_courses,
        "pending_reviews": pending_reviews,
        "weekly_exercises": weekly_exercises,
    }


def list_students(db: Session, teacher_id: str, class_id: int = None, page: int = None, page_size: int = None, keyword: str = None):
    class_ids = _teacher_class_ids(db, teacher_id)
    if class_id:
        if class_id not in class_ids:
            return [], 0
        class_ids = [class_id]
    if not class_ids:
        return [], 0
    query = (
        db.query(User, StudentClassEnrollment, Class)
        .join(StudentClassEnrollment, StudentClassEnrollment.user_id == User.id)
        .join(Class, Class.id == StudentClassEnrollment.class_id)
        .filter(User.role == "student", StudentClassEnrollment.class_id.in_(class_ids))
    )
    if keyword:
        query = query.filter(
            (User.id.like(f"%{keyword}%")) | (User.name.like(f"%{keyword}%"))
        )
    query = query.order_by(Class.id.asc(), StudentClassEnrollment.import_order.asc(), User.id.asc())
    total = query.count()
    if page and page_size:
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
    else:
        rows = query.all()
    result = []
    for s, enrollment, class_ in rows:
        progresses = (
            db.query(StudentProgress)
            .join(Course, Course.id == StudentProgress.course_id)
            .filter(
                StudentProgress.user_id == s.id,
                StudentProgress.course_id.in_(
                    db.query(Class.course_id).filter(Class.id.in_(class_ids))
                ),
            )
            .all()
        )
        total_progress = sum(p.learn_progress for p in progresses)
        avg_progress = int(total_progress / len(progresses)) if progresses else 0

        total_done = sum(p.questions_done for p in progresses)
        total_accuracy = sum(p.accuracy for p in progresses)
        avg_accuracy = int(total_accuracy / len(progresses)) if progresses else 0

        result.append({
            "serial_no": enrollment.import_order or 0,
            "id": s.id,
            "name": s.name,
            "major": s.major or "",
            "class_id": class_.id,
            "class_name": class_.name,
            "progress": avg_progress,
            "exercises": total_done,
            "accuracy": avg_accuracy,
        })
    return result, total


def list_all_projects(
    db: Session,
    status: str = None,
    page: int = None,
    page_size: int = None,
    teacher_id: str | None = None,
    keyword: str | None = None,
):
    query = db.query(Project)
    if teacher_id:
        student_ids = _teacher_student_ids(db, teacher_id)
        if student_ids:
            query = query.filter(Project.author_id.in_(student_ids))
        else:
            query = query.filter(False)
    if status:
        query = query.filter(Project.status == status)
    if keyword:
        query = query.filter(Project.title.like(f"%{keyword}%"))
    query = query.order_by(Project.date.desc())
    total = query.count()
    if page and page_size:
        projects = query.offset((page - 1) * page_size).limit(page_size).all()
    else:
        projects = query.all()
    return projects, total
