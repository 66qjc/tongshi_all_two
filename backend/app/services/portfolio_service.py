"""Portfolio service"""
from sqlalchemy.orm import Session
from app.models.entities import User, QuizAttempt, Project, StudentProgress, StudentClassEnrollment, Class


def get_portfolio(db: Session, user_id: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).count()
    correct = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id, QuizAttempt.is_correct == True,
    ).count()
    accuracy = int(correct / attempts * 100) if attempts > 0 else 0

    progresses = db.query(StudentProgress).filter(StudentProgress.user_id == user_id).all()
    total_progress = sum(p.learn_progress for p in progresses)
    visible_course_ids = {
        row.course_id
        for row in db.query(Class.course_id)
        .join(StudentClassEnrollment, StudentClassEnrollment.class_id == Class.id)
        .filter(StudentClassEnrollment.user_id == user_id)
        .all()
    }
    progress_course_ids = {p.course_id for p in progresses}
    denominator = len(visible_course_ids or progress_course_ids)
    avg_progress = int(total_progress / denominator) if denominator else 0

    projects = db.query(Project).filter(
        Project.author_id == user_id, Project.status == "approved",
    ).all()

    # Simulated radar data
    radar = {
        "理论基础": min(100, avg_progress + 10),
        "实践能力": min(100, len(projects) * 20),
        "创新思维": min(100, len(projects) * 15 + 20),
        "团队协作": min(100, attempts * 2),
        "社会传播": min(100, sum(p.likes for p in projects) * 5),
        "伦理意识": min(100, avg_progress),
    }

    timeline = []
    for p in projects:
        timeline.append({
            "type": "create",
            "title": f"提交作品「{p.title}」",
            "date": p.date,
        })

    return {
        "user": {"id": user.id, "name": user.name, "role": user.role, "major": user.major},
        "stats": {
            "study_hours": int(avg_progress * 0.5),
            "total_exercises": attempts,
            "accuracy": accuracy,
            "project_count": len(projects),
        },
        "radar": radar,
        "timeline": timeline,
        "projects": [
            {
                "id": p.id,
                "title": p.title,
                "author_id": p.author_id,
                "author_name": user.name,
                "major": p.major,
                "description": p.description,
                "tags": p.tags,
                "likes": p.likes,
                "featured": p.featured,
                "video_url": p.video_url,
                "report_url": p.report_url,
                "image_url": p.image_url,
                "status": p.status,
                "reject_reason": p.reject_reason,
                "date": p.date,
            }
            for p in projects
        ],
    }
