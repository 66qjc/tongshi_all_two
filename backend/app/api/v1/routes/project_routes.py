"""Project routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, ProjectCreate
from app.services.project_service import (
    list_approved_projects, get_project, get_user_projects,
    create_project, toggle_like,
)
from app.models.entities import User

router = APIRouter(prefix="/projects", tags=["projects"])


def _format_project(db: Session, p):
    author = db.query(User).filter(User.id == p.author_id).first()
    return {
        "id": p.id, "title": p.title, "author_id": p.author_id,
        "author_name": author.name if author else "",
        "major": p.major, "description": p.description,
        "tags": p.tags, "likes": p.likes, "featured": p.featured,
        "video_url": p.video_url, "report_url": p.report_url,
        "image_url": p.image_url, "link_url": getattr(p, "link_url", ""),
        "status": p.status,
        "reject_reason": p.reject_reason, "date": p.date,
    }


@router.get("", summary="作品广场", description="浏览所有已通过审核的项目作品")
def get_projects(db: Session = Depends(get_db), _: AuthUser = Depends(get_current_user)):
    projects = list_approved_projects(db)
    return success([_format_project(db, p) for p in projects])


@router.get("/mine", summary="我的作品", description="学生端：查看自己提交的所有作品")
def get_my_projects(db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    projects = get_user_projects(db, current_user.id)
    return success([_format_project(db, p) for p in projects])


@router.get("/{project_id}", summary="作品详情", description="查看指定作品的完整信息")
def get_project_detail(project_id: int, db: Session = Depends(get_db), _: AuthUser = Depends(get_current_user)):
    p = get_project(db, project_id)
    if not p:
        raise BusinessException(404, "作品不存在")
    return success(_format_project(db, p))


@router.post("", summary="提交作品", description="学生端：提交新的 AI 项目作品")
def create_new_project(data: ProjectCreate, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    p = create_project(db, current_user.id, data.model_dump())
    return success({"id": p.id})


@router.post("/{project_id}/like", summary="点赞/取消点赞", description="切换对指定作品的点赞状态，返回最新点赞数")
def like_project(project_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = toggle_like(db, current_user.id, project_id)
    if result is None:
        raise BusinessException(404, "作品不存在")
    return success(result)
