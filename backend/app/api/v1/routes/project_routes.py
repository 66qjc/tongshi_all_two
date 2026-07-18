"""Project routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, get_optional_user
from app.core.response import success, paginated_success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, ProjectCreate, ProjectUpdate
from app.services.project_service import (
    list_approved_projects, get_user_projects,
    create_project, toggle_like, update_project, delete_own_project, format_project,
    batch_load_liked_set, guest_like_project, get_public_or_accessible_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", summary="作品广场", description="浏览所有已通过审核的项目作品；游客可访问")
def get_projects(
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
    current_user: AuthUser | None = Depends(get_optional_user),
):
    projects, total = list_approved_projects(db, page, page_size)
    user_id = current_user.id if current_user else None
    liked = batch_load_liked_set(db, [p.id for p in projects], user_id) if user_id else set()
    return paginated_success(
        [format_project(db, p, user_id, liked_set=liked) for p in projects],
        total, page, page_size,
    )


@router.get("/mine", summary="我的作品", description="学生端：查看自己提交的所有作品")
def get_my_projects(
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    projects, total = get_user_projects(db, current_user.id, page, page_size)
    liked = batch_load_liked_set(db, [p.id for p in projects], current_user.id)
    return paginated_success([format_project(db, p, current_user.id, liked_set=liked) for p in projects], total, page, page_size)


@router.get("/{project_id}", summary="作品详情", description="已通过作品游客可看；未通过仅作者可看")
def get_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser | None = Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None
    p = get_public_or_accessible_project(db, project_id, user_id)
    if not p:
        raise BusinessException(404, "作品不存在")
    return success(format_project(db, p, user_id))


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


@router.delete("/{project_id}", summary="删除自己的作品", description="学生端：软删除自己的待审或已驳回作品")
def delete_my_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    delete_own_project(db, project_id, current_user)
    return success()


@router.post("/{project_id}/like", summary="点赞/取消点赞", description="切换对指定作品的点赞状态，返回最新点赞数")
def like_project(project_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = toggle_like(db, current_user.id, project_id)
    if result is None:
        raise BusinessException(404, "作品不存在")
    return success(result)


@router.post("/{project_id}/guest-like", summary="游客点赞", description="匿名点赞，仅增加计数，不可取消")
def guest_like(project_id: int, db: Session = Depends(get_db)):
    result = guest_like_project(db, project_id)
    if result is None:
        raise BusinessException(404, "作品不存在")
    return success(result)
