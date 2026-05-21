"""Teacher service"""
from sqlalchemy.orm import Session
from app.models.entities import User, Chapter, Project, QuizAttempt, StudentProgress, StudentClassEnrollment, Class


def get_teacher_stats(db: Session):
    total_students = db.query(User).filter(User.role == "student").count()
    published_chapters = db.query(Chapter).filter(Chapter.status == "已发布").count()
    pending_reviews = db.query(Project).filter(Project.status == "pending").count()
    weekly_exercises = db.query(QuizAttempt).count()  # simplified: total instead of weekly
    return {
        "total_students": total_students,
        "published_chapters": published_chapters,
        "pending_reviews": pending_reviews,
        "weekly_exercises": weekly_exercises,
    }


def list_students(db: Session, class_id: int = None):
    query = db.query(User).filter(User.role == "student")
    if class_id:
        query = (
            query.join(StudentClassEnrollment, StudentClassEnrollment.user_id == User.id)
            .filter(StudentClassEnrollment.class_id == class_id)
        )
    students = query.order_by(User.id).all()
    result = []
    for s in students:
        progresses = db.query(StudentProgress).filter(StudentProgress.user_id == s.id).all()
        total_progress = sum(p.learn_progress for p in progresses)
        avg_progress = int(total_progress / len(progresses)) if progresses else 0

        total_done = sum(p.questions_done for p in progresses)
        total_accuracy = sum(p.accuracy for p in progresses)
        avg_accuracy = int(total_accuracy / len(progresses)) if progresses else 0

        enrollment_query = (
            db.query(StudentClassEnrollment, Class)
            .join(Class, Class.id == StudentClassEnrollment.class_id)
            .filter(StudentClassEnrollment.user_id == s.id)
        )
        if class_id:
            enrollment_query = enrollment_query.filter(StudentClassEnrollment.class_id == class_id)
        enrollment = enrollment_query.order_by(StudentClassEnrollment.enrolled_at.desc()).first()
        class_id_value = enrollment[1].id if enrollment else None
        class_name = enrollment[1].name if enrollment else ""

        result.append({
            "id": s.id,
            "name": s.name,
            "major": s.major or "",
            "class_id": class_id_value,
            "class_name": class_name,
            "progress": avg_progress,
            "exercises": total_done,
            "accuracy": avg_accuracy,
        })
    return result


def list_all_projects(db: Session, status: str = None):
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    return query.order_by(Project.date.desc()).all()
