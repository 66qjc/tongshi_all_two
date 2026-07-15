"""Project service"""
import logging
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import BusinessException
from app.models.entities import Class, Course, Project, ProjectImage, ProjectLike, StudentClassEnrollment, User
from app.services.access_control_service import student_can_access_course
from app.services.notification_service import create_project_review_notification

logger = logging.getLogger(__name__)


def with_project_eager_load(query):
    """给作品查询添加预加载，避免 N+1 查询。"""
    return query.options(
        joinedload(Project.author),
        joinedload(Project.course),
        selectinload(Project.images),
        selectinload(Project.project_likes),
    )


def batch_load_liked_set(db: Session, project_ids: list[int], user_id: str | None) -> set[int]:
    """批量查询用户已点赞的作品 ID 集合，避免逐条查询。"""
    if not user_id or not project_ids:
        return set()
    rows = db.query(ProjectLike.project_id).filter(
        ProjectLike.user_id == user_id,
        ProjectLike.project_id.in_(project_ids),
    ).all()
    return {row[0] for row in rows}


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
    query = with_project_eager_load(
        db.query(Project).filter(Project.status == "approved").order_by(Project.date.desc())
    )
    total = db.query(Project).filter(Project.status == "approved").count()
    if page and page_size:
        projects = query.offset((page - 1) * page_size).limit(page_size).all()
    else:
        projects = query.all()
    return projects, total


def get_project(db: Session, project_id: int):
    return with_project_eager_load(
        db.query(Project).filter(Project.id == project_id)
    ).first()


def get_accessible_project(db: Session, project_id: int, user_id: str):
    """学生端作品详情：仅作者可看未审核作品，已通过作品对登录用户可见。"""
    project = get_project(db, project_id)
    if not project:
        return None
    if project.status == "approved" or project.author_id == user_id:
        return project
    return None


def get_user_projects(db: Session, user_id: str, page: int = None, page_size: int = None):
    query = with_project_eager_load(
        db.query(Project).filter(Project.author_id == user_id).order_by(Project.date.desc())
    )
    total = db.query(Project).filter(Project.author_id == user_id).count()
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
    """软删除作品，保留图片与点赞等关联事实。"""
    project = get_project(db, project_id)
    if not project or project.deleted_at is not None:
        return None
    if teacher_id and not _teacher_can_review_project(db, teacher_id, project):
        return None
    from app.schemas.common import AuthUser
    from app.services.soft_delete_service import soft_delete

    operator = AuthUser(id=teacher_id or project.author_id, name="", role="teacher")
    soft_delete(db, project, operator, action="project.delete")
    db.commit()
    logger.info("作品删除: project_id=%s, title=%s", project_id, project.title)
    return project


def format_project(db: Session, p, user_id: str | None = None, liked_set: set[int] | None = None) -> dict:
    """将 Project ORM 对象格式化为 API 响应 dict（唯一规范版本）。

    所有路由统一调用此函数。传入 user_id 时返回 is_liked 字段。
    传入 liked_set（预批量查询的已点赞作品 ID 集合）可避免逐条查询。
    调用方应使用 with_project_eager_load() 预加载 relationship，避免 N+1。
    """
    # 作者：优先使用预加载的 relationship，回退到查询
    author = p.author if p.author else db.query(User).filter(User.id == p.author_id).first()

    # 课程名称：优先使用预加载的 relationship
    course_name = ""
    if p.course_id:
        course = p.course if p.course else db.query(Course).filter(Course.id == p.course_id).first()
        course_name = course.name if course else ""

    # 图片列表：使用预加载的 images relationship
    images = [
        {"id": img.id, "image_url": img.image_url, "sort_order": img.sort_order, "file_id": img.file_id}
        for img in sorted(p.images, key=lambda item: (item.sort_order, item.id))
    ] if p.images else []
    if not images and p.image_url:
        images = [{"image_url": p.image_url, "sort_order": 0}]

    # 点赞状态：优先使用批量预查的 liked_set，回退到预加载 relationship，最终单条查询
    is_liked = False
    if user_id:
        if liked_set is not None:
            is_liked = p.id in liked_set
        elif p.project_likes is not None:
            is_liked = any(like.user_id == user_id for like in p.project_likes)
        else:
            is_liked = db.query(ProjectLike).filter(
                ProjectLike.user_id == user_id,
                ProjectLike.project_id == p.id,
            ).first() is not None

    return {
        "id": p.id,
        "title": p.title,
        "author_id": p.author_id,
        "author_name": author.name if author else "",
        "course_id": p.course_id,
        "course_name": course_name,
        "major": p.major,
        "description": p.description,
        "tags": p.tags or [],
        "likes": p.likes,
        "is_liked": is_liked,
        "featured": p.featured,
        "video_url": p.video_url or "",
        "report_url": p.report_url or "",
        "image_url": p.image_url or "",
        "images": images,
        "link_url": p.link_url or "",
        "status": p.status or "",
        "reject_reason": p.reject_reason or "",
        "date": p.date or "",
        "report_file_id": p.report_file_id,
        "cover_file_id": p.cover_file_id,
    }


def list_liked_projects(db: Session, user_id: str) -> list:
    """获取用户点赞（收藏）过的所有作品"""
    likes = db.query(ProjectLike).filter(ProjectLike.user_id == user_id).all()
    project_ids = [lk.project_id for lk in likes]
    if not project_ids:
        return []
    projects = with_project_eager_load(
        db.query(Project).filter(Project.id.in_(project_ids))
    ).all()
    # 用户赞过的作品自己一定在 liked_set 中，直接传入避免逐条查询
    liked_set = set(project_ids)
    return [format_project(db, proj, user_id, liked_set=liked_set) for proj in projects]
