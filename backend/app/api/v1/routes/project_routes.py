"""Project routes"""
import hashlib
import threading
import time

from fastapi import APIRouter, Depends, Request
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

# 游客点赞限流仍是单 worker 内存模式；锁只保证单进程内检查与写入原子。
_guest_like_last: dict[str, float] = {}
_guest_like_lock = threading.Lock()
_guest_like_last_cleanup = 0.0
_GUEST_LIKE_COOLDOWN = 3.0  # 同一 IP 对同一作品最短间隔秒数
_GUEST_LIKE_MAX_ENTRIES = 10_000


def _guest_like_project_identity(project) -> str:
    """生成包含作品归属与提交信息的短标识，避免主键复用继承旧限流状态。"""
    raw = "".join(str(value or "") for value in (
        project.id,
        project.author_id,
        project.date,
        project.title,
        project.report_file_id,
        project.cover_file_id,
        project.link_url,
    ))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _reserve_guest_like(rate_key: str) -> float:
    """原子检查并预占本次点赞窗口，返回单调时钟时间戳。"""
    global _guest_like_last_cleanup
    now = time.monotonic()
    with _guest_like_lock:
        if (
            now - _guest_like_last_cleanup >= _GUEST_LIKE_COOLDOWN
            or len(_guest_like_last) >= _GUEST_LIKE_MAX_ENTRIES
        ):
            expired_before = now - _GUEST_LIKE_COOLDOWN
            expired_keys = [
                key for key, last_at in _guest_like_last.items()
                if last_at <= expired_before
            ]
            for key in expired_keys:
                _guest_like_last.pop(key, None)
            _guest_like_last_cleanup = now

        last = _guest_like_last.get(rate_key)
        if last is not None and now - last < _GUEST_LIKE_COOLDOWN:
            raise BusinessException(429, "操作过于频繁，请稍后再试")

        if len(_guest_like_last) >= _GUEST_LIKE_MAX_ENTRIES:
            oldest_key = min(_guest_like_last, key=_guest_like_last.get)
            _guest_like_last.pop(oldest_key, None)
        _guest_like_last[rate_key] = now
    return now


def _release_guest_like_reservation(rate_key: str, reserved_at: float) -> None:
    """点赞未落库时撤销当前请求的限流预占。"""
    with _guest_like_lock:
        if _guest_like_last.get(rate_key) == reserved_at:
            _guest_like_last.pop(rate_key, None)


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
def guest_like(project_id: int, request: Request, db: Session = Depends(get_db)):
    from app.models.entities import Project as ProjectModel
    # 先验证作品有效性（不存在或未通过审核直接 404，不消耗限流配额）
    project = db.query(ProjectModel).filter(
        ProjectModel.id == project_id,
        ProjectModel.deleted_at.is_(None),
    ).first()
    if not project or project.status != "approved":
        raise BusinessException(404, "作品不存在")

    client_ip = request.client.host if request.client else "unknown"
    project_identity = _guest_like_project_identity(project)
    rate_key = f"{client_ip}:{project_id}:{project_identity}"
    reserved_at = _reserve_guest_like(rate_key)
    try:
        result = guest_like_project(db, project_id)
    except Exception:
        _release_guest_like_reservation(rate_key, reserved_at)
        raise
    if result is None:
        _release_guest_like_reservation(rate_key, reserved_at)
        raise BusinessException(404, "作品不存在")
    return success(result)
