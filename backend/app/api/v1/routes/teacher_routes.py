"""Teacher routes"""
import io
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, ProjectReviewAction
from app.services.teacher_service import get_teacher_stats, list_students, list_all_projects
from app.services.project_service import approve_project, reject_project
from app.models.entities import User, Project

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/stats", summary="工作台概览", description="教师端：返回总学生数、已发布章节数、待审核作品数、练习题量等教学数据")
def teacher_stats(db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    return success(get_teacher_stats(db))


@router.get("/students", summary="学生数据", description="教师端：返回所有学生的学号、姓名、专业、班级、学习进度和练习统计")
def get_students(
    class_id: int = None,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    return success(list_students(db, class_id))


@router.get("/projects", summary="作品审核列表", description="教师端：按状态筛选所有学生作品，默认返回全部")
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
            "image_url": p.image_url, "link_url": getattr(p, "link_url", ""), "status": p.status,
            "reject_reason": p.reject_reason, "date": p.date,
        })
    return success(result)


@router.post("/projects/{project_id}/approve", summary="通过作品审核", description="教师端：将指定作品设为审核通过")
def approve(project_id: int, db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    p = approve_project(db, project_id)
    if not p:
        raise BusinessException(404, "作品不存在")
    return success()


@router.post("/projects/{project_id}/reject", summary="驳回作品", description="教师端：驳回指定作品，需填写驳回原因")
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


@router.get("/projects/batch-download", summary="批量下载作品报告", description="教师端：打包下载所有已通过作品的 PDF 报告为 ZIP 文件")
def batch_download_projects(
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("teacher")),
):
    projects = (
        db.query(Project)
        .filter(Project.status == "approved", Project.report_url != "", Project.report_url.isnot(None))
        .all()
    )
    if not projects:
        raise BusinessException(404, "没有可下载的作品报告")

    upload_dir = Path(__file__).resolve().parents[3] / "uploads"
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in projects:
            report_filename = Path(p.report_url).name
            file_path = upload_dir / report_filename
            if not file_path.exists():
                continue
            author = db.query(User).filter(User.id == p.author_id).first()
            author_name = author.name if author else p.author_id
            ext = file_path.suffix or ".pdf"
            safe_title = "".join(c for c in p.title if c not in r'\\/:*?"<>|')
            inner_name = f"{author_name}_{safe_title}{ext}"
            zf.write(file_path, inner_name)

    if zip_buffer.tell() == 0:
        raise BusinessException(404, "没有可下载的作品报告文件")

    zip_buffer.seek(0)
    today = datetime.now().strftime("%Y%m%d")
    filename = f"project_reports_{today}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
