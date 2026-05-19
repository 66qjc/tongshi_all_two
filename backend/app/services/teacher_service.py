"""Teacher service"""
from sqlalchemy.orm import Session
from app.models.entities import User, Chapter, Project, QuizAttempt, StudentProgress


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


def list_students(db: Session):
    students = db.query(User).filter(User.role == "student").all()
    result = []
    for s in students:
        progresses = db.query(StudentProgress).filter(StudentProgress.user_id == s.id).all()
        total_progress = sum(p.learn_progress for p in progresses)
        avg_progress = int(total_progress / len(progresses)) if progresses else 0

        total_done = sum(p.questions_done for p in progresses)
        total_accuracy = sum(p.accuracy for p in progresses)
        avg_accuracy = int(total_accuracy / len(progresses)) if progresses else 0

        result.append({
            "id": s.id,
            "name": s.name,
            "major": s.major or "",
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
