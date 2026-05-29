"""Project service"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Project, ProjectImage, ProjectLike, User
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)


def normalize_project_images(data: dict) -> list[str]:
    image_urls = [str(item).strip() for item in (
        data.get("image_urls") or []) if str(item).strip()]
    single = str(data.get("image_url", "")).strip()
    if not image_urls and single:
        image_urls = [single]
    return image_urls[:3]


def sync_project_images(project: Project, image_urls: list[str], image_file_ids: list[int] | None = None) -> None:
    project.images.clear()
    for index, image_url in enumerate(image_urls):
        file_id = image_file_ids[index] if image_file_ids and index < len(
            image_file_ids) else None
        project.images.append(ProjectImage(
            image_url=image_url, sort_order=index, file_id=file_id))
    project.image_url = image_urls[0] if image_urls else ""


def list_approved_projects(db: Session, page: int = None, page_size: int = None):
    query = db.query(Project).filter(Project.status == "approved").order_by(Project.date.desc())
    total = query.count()
    if page and page_size:
        projects = query.offset((page - 1) * page_size).limit(page_size).all()
    else:
        projects = query.all()
    return projects, total


def get_project(db: Session, project_id: int):
    return db.query(Project).filter(Project.id == project_id).first()


def can_view_project(project: Project, user_id: str, role: str) -> bool:
    if project.status == "approved":
        return True
    if role in {"teacher", "admin"}:
        return True
    return project.author_id == user_id


def get_user_projects(db: Session, user_id: str, page: int = None, page_size: int = None):
    query = db.query(Project).filter(Project.author_id == user_id).order_by(Project.date.desc())
    total = query.count()
    if page and page_size:
        projects = query.offset((page - 1) * page_size).limit(page_size).all()
    else:
        projects = query.all()
    return projects, total


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
        image_url="",
        link_url=data.get("link_url", ""),
        report_file_id=data.get("report_file_id"),
        cover_file_id=data.get("cover_file_id"),
    )
    image_urls = normalize_project_images(data)
    image_file_ids = data.get("image_file_ids") or []
    sync_project_images(project, image_urls, image_file_ids)
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info("作品提交: user_id=%s, title=%s, id=%s",
                user_id, project.title, project.id)
    return project


def update_project(db: Session, project_id: int, user_id: str, data: dict):
    project = get_project(db, project_id)
    if not project:
        return None
    if project.author_id != user_id:
        raise BusinessException(403, "只能修改自己的作品")
    if project.status != "rejected":
        raise BusinessException(400, "当前作品不可重新提交")

    project.title = data.get("title", project.title)
    project.description = data.get("description", "")
    project.tags = data.get("tags") or []
    project.video_url = data.get("video_url", "")
    project.report_url = data.get("report_url", "")
    project.link_url = data.get("link_url", "")
    project.status = "pending"
    project.reject_reason = ""
    if data.get("report_file_id") is not None:
        project.report_file_id = data["report_file_id"]
    if data.get("cover_file_id") is not None:
        project.cover_file_id = data["cover_file_id"]
    image_file_ids = data.get("image_file_ids") or []
    sync_project_images(
        project, normalize_project_images(data), image_file_ids)

    db.commit()
    db.refresh(project)
    logger.info("作品重新提交: user_id=%s, project_id=%s, title=%s",
                user_id, project.id, project.title)
    return project


def toggle_like(db: Session, user_id: str, project_id: int):
    project = get_project(db, project_id)
    if not project:
        return None
    if project.status != "approved":
        raise BusinessException(400, "作品未通过审核，暂不能点赞")
    existing = db.query(ProjectLike).filter(
        ProjectLike.user_id == user_id, ProjectLike.project_id == project_id).first()
    if existing:
        db.delete(existing)
        project.likes = max(0, project.likes - 1)
    else:
        db.add(ProjectLike(user_id=user_id, project_id=project_id))
        project.likes += 1
    db.commit()
    return {"liked": existing is None, "likes": project.likes}


def approve_project(db: Session, project_id: int):
    project = get_project(db, project_id)
    if not project:
        return None
    project.status = "approved"
    project.reject_reason = ""
    db.commit()
    logger.info("作品审核通过: project_id=%s, title=%s", project_id, project.title)
    return project


def reject_project(db: Session, project_id: int, reason: str):
    project = get_project(db, project_id)
    if not project:
        return None
    project.status = "rejected"
    project.reject_reason = reason
    create_notification(
        db,
        user_id=project.author_id,
        type_="project_rejected",
        title="作品被驳回，请修改",
        content=f"你的作品「{project.title}」被驳回，原因：{reason or '请根据教师意见修改后重新提交'}",
        related_type="project",
        related_id=project.id,
    )
    db.commit()
    logger.info("作品驳回: project_id=%s, title=%s, reason=%s",
                project_id, project.title, reason)
    return project


def format_project(db: Session, p) -> dict:
    """将 Project ORM 对象格式化为 API 响应 dict"""
    from app.models.entities import User as UserModel
    author = db.query(UserModel).filter(UserModel.id == p.author_id).first()
    images = [
        {"id": image.id, "image_url": image.image_url,
            "sort_order": image.sort_order}
        for image in sorted(p.images, key=lambda item: (item.sort_order, item.id))
    ] if hasattr(p, "images") and p.images else []
    if not images and p.image_url:
        images = [{"image_url": p.image_url, "sort_order": 0}]
    return {
        "id": p.id,
        "title": p.title,
        "author_id": p.author_id,
        "author_name": author.name if author else "",
        "major": p.major,
        "description": p.description,
        "tags": p.tags if hasattr(p, "tags") else "",
        "likes": p.likes,
        "featured": p.featured if hasattr(p, "featured") else False,
        "video_url": p.video_url if hasattr(p, "video_url") else "",
        "report_url": p.report_url if hasattr(p, "report_url") else "",
        "image_url": p.image_url if hasattr(p, "image_url") else "",
        "images": images,
        "link_url": getattr(p, "link_url", ""),
        "status": p.status if hasattr(p, "status") else "",
        "reject_reason": p.reject_reason if hasattr(p, "reject_reason") else "",
        "date": p.date if hasattr(p, "date") else "",
    }


def list_liked_projects(db: Session, user_id: str) -> list:
    """获取用户点赞（收藏）过的所有作品"""
    likes = db.query(ProjectLike).filter(ProjectLike.user_id == user_id).all()
    project_ids = [lk.project_id for lk in likes]
    if not project_ids:
        return []
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
    return [format_project(db, proj) for proj in projects]
