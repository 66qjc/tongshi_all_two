"""资料服务。"""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.entities import Class, Course, CourseStage, Material, StoredFile, StudentClassEnrollment
from app.services.file_service import build_x_accel_redirect_path


def list_materials(
    db: Session,
    course_id: int | None = None,
    teacher_id: str | None = None,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    include_public_sources: bool = True,
):
    # 正常业务列表只返回未软删资料及其所属活跃课程。
    query = db.query(Material).join(Course, Course.id == Material.course_id).filter(
        Material.deleted_at.is_(None),
        Course.deleted_at.is_(None),
    )
    if teacher_id is not None:
        if include_public_sources:
            query = query.filter(
                or_(Course.created_by == teacher_id, Course.is_public.is_(True)))
        else:
            query = query.filter(Course.created_by == teacher_id)
    if course_id is not None:
        query = query.filter(Material.course_id == course_id)
    if keyword:
        query = query.filter(Material.title.ilike(f"%{keyword.strip()}%"))
    total = query.count()
    if page and page_size:
        materials = query.order_by(Material.course_id, Material.id).offset((page - 1) * page_size).limit(page_size).all()
    else:
        materials = query.order_by(Material.course_id, Material.id).all()
    return materials, total


def can_view_course_materials(db: Session, course_id: int, user_id: str, role: str) -> bool:
    """校验课程资料访问权限：学生限所在活跃课程，教师限自有或公共活跃课程。"""
    if role == "student":
        from app.services.access_control_service import student_can_access_course
        return student_can_access_course(db, user_id, course_id)
    if role == "teacher":
        return db.query(Course).filter(
            Course.id == course_id,
            Course.deleted_at.is_(None),
            or_(Course.created_by == user_id, Course.is_public.is_(True)),
        ).first() is not None
    return db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None),
    ).first() is not None


def create_material(
    db: Session,
    course_id: int,
    type_: str,
    title: str,
    url: str = "",
    size: str = "0 MB",
    file_id: int | None = None,
    stage_id: int | None = None,
    teacher_id: str | None = None,
):
    query = db.query(Course).filter(Course.id == course_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    course = query.first()
    if not course:
        return None
    if stage_id is not None:
        stage = db.query(CourseStage).filter(
            CourseStage.id == stage_id,
            CourseStage.course_id == course_id,
        ).first()
        if not stage:
            raise BusinessException(400, "阶段不存在或不属于该课程")
    material = Material(
        course_id=course_id,
        type=type_,
        title=title,
        url=url,
        size=size,
        date=datetime.now().strftime("%Y-%m-%d"),
        file_id=file_id,
        stage_id=stage_id,
    )
    db.add(material)
    db.flush()
    from app.services.material_preview_service import bootstrap_material_preview
    # PDF 创建后立即抽取摘要；视频/其它类型仅建立 pending 预览记录。
    bootstrap_material_preview(db, material)
    db.commit()
    db.refresh(material)
    return material


def update_material(
    db: Session,
    material_id: int,
    title: str | None = None,
    stage_id: int | None = None,
    teacher_id: str | None = None,
    clear_stage_id: bool = False,
):
    query = db.query(Material).join(Course, Course.id == Material.course_id).filter(Material.id == material_id)
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    material = query.first()
    if not material:
        return None
    if material.source_material_id is not None:
        raise BusinessException(400, "公共课程同步内容不能编辑")
    if title is not None:
        material.title = title
    if clear_stage_id:
        # 前端显式发送 stage_id: null，表示将资料移出阶段
        material.stage_id = None
    elif stage_id is not None:
        stage = db.query(CourseStage).filter(
            CourseStage.id == stage_id,
            CourseStage.course_id == material.course_id,
        ).first()
        if not stage:
            raise BusinessException(400, "阶段不存在或不属于该课程")
        material.stage_id = stage_id
    db.commit()
    db.refresh(material)
    return material


def delete_material(db: Session, material_id: int, teacher_id: str | None = None):
    query = db.query(Material).join(Course, Course.id == Material.course_id).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None),
    )
    if teacher_id is not None:
        query = query.filter(Course.created_by == teacher_id)
    m = query.first()
    if not m:
        return False
    from app.schemas.common import AuthUser
    from app.services.soft_delete_service import soft_delete

    operator = AuthUser(id=teacher_id or "", name="", role="teacher")
    soft_delete(db, m, operator, action="material.delete")
    db.commit()
    return True


def format_material_preview(preview) -> dict | None:
    """格式化资料预览元数据为字典。"""
    if not preview:
        return None
    return {
        "status": preview.status,
        "cover_file_id": preview.cover_file_id,
        "summary": preview.summary or "",
        "page_count": preview.page_count or 0,
        "duration_seconds": preview.duration_seconds or 0,
        "resolution": preview.resolution or "",
        "error_message": preview.error_message or "",
    }


def format_material_preview_for_material(db: Session, material: Material) -> dict | None:
    """格式化资料预览；PDF 在读路径对 pending/缺失记录做一次懒生成。"""
    from app.services.material_preview_service import hydrate_material_preview_for_read

    hydrate_material_preview_for_read(db, material)
    return format_material_preview(material.preview)


def resolve_material_file_for_user(db: Session, material_id: int, user_id: str, role: str):
    """校验资料访问权限并返回资料、文件记录和 Nginx 内部路径。"""
    material = db.query(Material).join(Course, Course.id == Material.course_id).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None),
        Course.deleted_at.is_(None),
    ).first()
    if not material:
        return None, None, ""
    if not can_view_course_materials(db, material.course_id, user_id, role):
        return None, None, ""
    if not material.file_id:
        raise BusinessException(404, "资料文件不存在")

    stored = db.query(StoredFile).filter(StoredFile.id == material.file_id).first()
    if not stored:
        raise BusinessException(404, "资料文件不存在")
    if stored.storage_provider != "local":
        raise BusinessException(400, "当前试点仅支持本地文件预览")
    try:
        accel_path = build_x_accel_redirect_path(stored.object_key)
    except ValueError:
        raise BusinessException(400, "资料文件路径不合法")
    return material, stored, accel_path
