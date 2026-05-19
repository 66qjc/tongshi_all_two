"""Project service"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.entities import Project, ProjectLike, User

logger = logging.getLogger(__name__)


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
        title=data.get("title"),
        description=data.get("description", ""),
        tags=data.get("tags") or [],
        video_url=data.get("video_url", ""),
        report_url=data.get("report_url", ""),
        image_url=data.get("image_url", ""),
        link_url=data.get("link_url", ""),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info(f"作品提交: user_id={user_id}, title={project.title}, id={project.id}")
    return project


def toggle_like(db: Session, user_id: str, project_id: int):
    project = get_project(db, project_id)
    if not project:
        return None
    existing = db.query(ProjectLike).filter(ProjectLike.user_id == user_id, ProjectLike.project_id == project_id).first()
    if existing:
        db.delete(existing)
        project.likes = max(0, project.likes - 1)
    else:
        db.add(ProjectLike(user_id=user_id, project_id=project_id))
        project.likes += 1
    db.commit()
    return {"liked": existing is None, "likes": project.likes}


def approve_project(db: Session, project_id: int):
    p = get_project(db, project_id)
    if not p:
        return None
    p.status = "approved"
    p.reject_reason = ""
    db.commit()
    logger.info(f"作品审核通过: project_id={project_id}, title={p.title}")
    return p


def reject_project(db: Session, project_id: int, reason: str):
    p = get_project(db, project_id)
    if not p:
        return None
    p.status = "rejected"
    p.reject_reason = reason
    db.commit()
    logger.info(f"作品驳回: project_id={project_id}, title={p.title}, reason={reason}")
    return p
