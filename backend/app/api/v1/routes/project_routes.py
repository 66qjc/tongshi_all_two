"""Project routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success, paginated_success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, ProjectCreate, ProjectUpdate
from app.services.project_service import (
    list_approved_projects, get_project, get_user_projects,
    create_project, toggle_like, update_project, format_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", summary="作品广场", description="浏览所有已通过审核的项目作品")
def get_projects(
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    projects, total = list_approved_projects(db, page, page_size)
    return paginated_success([format_project(db, p) for p in projects], total, page, page_size)


@router.get("/mine", summary="我的作品", description="学生端：查看自己提交的所有作品")
def get_my_projects(
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    projects, total = get_user_projects(db, current_user.id, page, page_size)
    return paginated_success([format_project(db, p) for p in projects], total, page, page_size)


@router.get("/{project_id}", summary="作品详情", description="查看指定作品的完整信息")
def get_project_detail(project_id: int, db: Session = Depends(get_db), _: AuthUser = Depends(get_current_user)):
    p = get_project(db, project_id)
    if not p:
        raise BusinessException(404, "作品不存在")
    return success(format_project(db, p))


@router.post("", summary="提交作品", description="学生端：提交新的 AI 项目作品")
def create_new_project(data: ProjectCreate, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    p = create_project(db, current_user.id, data.model_dump())
    return success({"id": p.id})


@router.put("/{project_id}", summary="修改后重新提交作品", description="学生端：修改被驳回的原作品并重新提交审核")
def update_existing_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    p = update_project(db, project_id, current_user.id, data.model_dump())
    if not p:
        raise BusinessException(404, "作品不存在")
    return success({"id": p.id})


@router.post("/{project_id}/like", summary="点赞/取消点赞", description="切换对指定作品的点赞状态，返回最新点赞数")
def like_project(project_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = toggle_like(db, current_user.id, project_id)
    if result is None:
        raise BusinessException(404, "作品不存在")
    return success(result)
