"""Project service"""
import logging
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Class, Course, Project, ProjectImage, ProjectLike, StudentClassEnrollment, User
from app.services.access_control_service import student_can_access_course
from app.services.notification_service import create_project_review_notification

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


def _student_can_submit_to_course(db: Session, user_id: str, course_id: int) -> bool:
    return student_can_access_course(db, user_id, course_id)


def _teacher_can_review_project(db: Session, teacher_id: str, project: Project) -> bool:
    if project.course_id is not None:
        return db.query(Course.id).filter(
            Course.id == project.course_id,
            Course.created_by == teacher_id,
        ).first() is not None

    return db.query(StudentClassEnrollment.id).join(
        Class, Class.id == StudentClassEnrollment.class_id
    ).filter(
        StudentClassEnrollment.user_id == project.author_id,
        Class.created_by == teacher_id,
    ).first() is not None


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


def get_accessible_project(db: Session, project_id: int, user_id: str):
    """学生端作品详情：仅作者可看未审核作品，已通过作品对登录用户可见。"""
    project = get_project(db, project_id)
    if not project:
        return None
    if project.status == "approved" or project.author_id == user_id:
        return project
    return None


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
    course_id = data.get("course_id")
    if not course_id or not _student_can_submit_to_course(db, user_id, course_id):
        raise BusinessException(403, "只能选择自己已加入的课程提交作品")

    project = Project(
        author_id=user_id,
        course_id=course_id,
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

    course_id = data.get("course_id")
    if not course_id or not _student_can_submit_to_course(db, user_id, course_id):
        raise BusinessException(403, "只能选择自己已加入的课程提交作品")

    project.title = data.get("title", project.title)
    project.course_id = course_id
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


def withdraw_project(db: Session, project_id: int, user_id: str):
    project = get_project(db, project_id)
    if not project:
        return None
    if project.author_id != user_id:
        raise BusinessException(403, "只能撤回自己的作品")
    if project.status == "withdrawn":
        raise BusinessException(400, "作品已撤回")

    project.status = "withdrawn"
    project.reject_reason = ""
    project.featured = False
    db.commit()
    db.refresh(project)
    logger.info("作品撤回: user_id=%s, project_id=%s, title=%s", user_id, project.id, project.title)
    return project


def toggle_like(db: Session, user_id: str, project_id: int):
    project = get_project(db, project_id)
    if not project:
        return None

    existing = db.query(ProjectLike).filter(
        ProjectLike.user_id == user_id, ProjectLike.project_id == project_id).first()

    if existing:
        db.delete(existing)
        # 原子递减 likes，钳制到 0 防止负数
        db.execute(
            Project.__table__.update()
            .where(Project.id == project_id)
            .values(likes=func.max(Project.likes - 1, 0))
        )
        db.commit()
        db.refresh(project)
        return {"liked": False, "likes": max(0, project.likes)}
    else:
        db.add(ProjectLike(user_id=user_id, project_id=project_id))
        # 原子递增 likes，避免并发竞态
        db.execute(
            Project.__table__.update()
            .where(Project.id == project_id)
            .values(likes=Project.likes + 1)
        )
        db.commit()
        db.refresh(project)
        return {"liked": True, "likes": project.likes}


def approve_project(db: Session, project_id: int, teacher_id: str | None = None):
    project = get_project(db, project_id)
    if not project:
        return None
    if teacher_id and not _teacher_can_review_project(db, teacher_id, project):
        return None
    project.status = "approved"
    project.reject_reason = ""
    create_project_review_notification(db, project, approved=True)
    db.commit()
    logger.info("作品审核通过: project_id=%s, title=%s", project_id, project.title)
    return project


def reject_project(db: Session, project_id: int, reason: str, teacher_id: str | None = None):
    project = get_project(db, project_id)
    if not project:
        return None
    if teacher_id and not _teacher_can_review_project(db, teacher_id, project):
        return None
    project.status = "rejected"
    project.reject_reason = reason
    create_project_review_notification(db, project, approved=False, reason=reason)
    db.commit()
    logger.info("作品驳回: project_id=%s, title=%s, reason=%s",
                project_id, project.title, reason)
    return project


def delete_project(db: Session, project_id: int, teacher_id: str | None = None):
    """删除作品及其关联数据"""
    project = get_project(db, project_id)
    if not project:
        return None
    if teacher_id and not _teacher_can_review_project(db, teacher_id, project):
        return None
    # 删除关联的点赞记录
    db.query(ProjectLike).filter(ProjectLike.project_id == project_id).delete()
    # 删除关联的图片记录
    db.query(ProjectImage).filter(ProjectImage.project_id == project_id).delete()
    # 删除作品
    db.delete(project)
    db.commit()
    logger.info("作品删除: project_id=%s, title=%s", project_id, project.title)
    return project


def format_project(db: Session, p, user_id: str | None = None) -> dict:
    """将 Project ORM 对象格式化为 API 响应 dict（唯一规范版本）。

    所有路由统一调用此函数，避免 _format_project 重复定义。
    传入 user_id 时返回 is_liked 字段。
    """
    author = db.query(User).filter(User.id == p.author_id).first()
    course_id = getattr(p, "course_id", None)
    course_name = ""
    if course_id:
        course = getattr(p, "course", None) or db.query(Course).filter(Course.id == course_id).first()
        course_name = course.name if course else ""
    images = [
        {"id": image.id, "image_url": image.image_url,
            "sort_order": image.sort_order, "file_id": image.file_id}
        for image in sorted(p.images, key=lambda item: (item.sort_order, item.id))
    ] if hasattr(p, "images") and p.images else []
    if not images and p.image_url:
        images = [{"image_url": p.image_url, "sort_order": 0}]

    # 查询当前用户是否已点赞
    is_liked = False
    if user_id:
        is_liked = db.query(ProjectLike).filter(
            ProjectLike.user_id == user_id,
            ProjectLike.project_id == p.id
        ).first() is not None

    return {
        "id": p.id,
        "title": p.title,
        "author_id": p.author_id,
        "author_name": author.name if author else "",
        "course_id": course_id,
        "course_name": course_name,
        "major": p.major,
        "description": p.description,
        "tags": p.tags if hasattr(p, "tags") else [],
        "likes": p.likes,
        "is_liked": is_liked,
        "featured": p.featured if hasattr(p, "featured") else False,
        "video_url": p.video_url if hasattr(p, "video_url") else "",
        "report_url": p.report_url if hasattr(p, "report_url") else "",
        "image_url": p.image_url if hasattr(p, "image_url") else "",
        "images": images,
        "link_url": getattr(p, "link_url", ""),
        "status": p.status if hasattr(p, "status") else "",
        "reject_reason": p.reject_reason if hasattr(p, "reject_reason") else "",
        "date": p.date if hasattr(p, "date") else "",
        "report_file_id": getattr(p, "report_file_id", None),
        "cover_file_id": getattr(p, "cover_file_id", None),
    }


def list_liked_projects(db: Session, user_id: str) -> list:
    """获取用户点赞（收藏）过的所有作品"""
    likes = db.query(ProjectLike).filter(ProjectLike.user_id == user_id).all()
    project_ids = [lk.project_id for lk in likes]
    if not project_ids:
        return []
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
    return [format_project(db, proj, user_id) for proj in projects]
