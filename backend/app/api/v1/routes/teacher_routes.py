"""Teacher routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, ProjectReviewAction
from app.services.teacher_service import get_teacher_stats, list_students, list_all_projects
from app.services.project_service import approve_project, reject_project
from app.models.entities import User

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/stats")
def teacher_stats(db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    return success(get_teacher_stats(db))


@router.get("/students")
def get_students(db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    return success(list_students(db))


@router.get("/projects")
def get_all_projects(
    status: str = None,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    projects = list_all_projects(db, status)
    result = []
    for p in projects:
        author = db.query(User).filter(User.id == p.author_id).first()
        result.append({
            "id": p.id, "title": p.title, "author_id": p.author_id,
            "author_name": author.name if author else "",
            "major": p.major, "description": p.description,
            "tags": p.tags, "likes": p.likes, "featured": p.featured,
            "video_url": p.video_url, "report_url": p.report_url,
            "image_url": p.image_url, "status": p.status,
            "reject_reason": p.reject_reason, "date": p.date,
        })
    return success(result)


@router.post("/projects/{project_id}/approve")
def approve(project_id: int, db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    p = approve_project(db, project_id)
    if not p:
        raise BusinessException(404, "作品不存在")
    return success()


@router.post("/projects/{project_id}/reject")
def reject(
    project_id: int,
    data: ProjectReviewAction,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    p = reject_project(db, project_id, data.reason or "")
    if not p:
        raise BusinessException(404, "作品不存在")
    return success()
