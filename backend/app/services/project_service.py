"""Project service"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.entities import Project, ProjectLike, User


def list_approved_projects(db: Session):
    return db.query(Project).filter(Project.status == "approved").order_by(Project.date.desc()).all()


def get_project(db: Session, project_id: int):
    return db.query(Project).filter(Project.id == project_id).first()


def get_user_projects(db: Session, user_id: str):
    return db.query(Project).filter(Project.author_id == user_id).order_by(Project.date.desc()).all()


def create_project(db: Session, user_id: str, data: dict):
    user = db.query(User).filter(User.id == user_id).first()
    project = Project(
        author_id=user_id,
        major=user.major if user else "",
        date=datetime.now().strftime("%Y-%m-%d"),
        **data,
    )
    db.add(project)
    db.commit()
    return project


def toggle_like(db: Session, user_id: str, project_id: int):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None

    existing = db.query(ProjectLike).filter(
        ProjectLike.user_id == user_id,
        ProjectLike.project_id == project_id,
    ).first()

    if existing:
        db.delete(existing)
        project.likes = max(0, project.likes - 1)
        liked = False
    else:
        like = ProjectLike(user_id=user_id, project_id=project_id)
        db.add(like)
        project.likes += 1
        liked = True

    db.commit()
    return {"liked": liked, "likes": project.likes}


def approve_project(db: Session, project_id: int):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
    project.status = "approved"
    db.commit()
    return project


def reject_project(db: Session, project_id: int, reason: str = ""):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
    project.status = "rejected"
    project.reject_reason = reason
    db.commit()
    return project
