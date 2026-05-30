"""Teacher routes"""
import io
import os
import tempfile
import zipfile
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.core.security import require_role
from app.core.response import success, paginated_success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, ProjectReviewAction
from app.services.teacher_service import get_teacher_stats, list_students, list_all_projects
from app.services.project_service import approve_project, reject_project, format_project
from app.services.file_service import resolve_file_stream
from app.models.entities import User, Project, Class
from openpyxl import Workbook

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/stats", summary="工作台概览", description="教师端：返回总学生数、我的课程数、待审核作品数、练习题量等教学数据")
def teacher_stats(db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    return success(get_teacher_stats(db, current_user.id))


@router.get("/students", summary="学生成绩", description="教师端：返回所有学生的学号、姓名、专业、班级、学习进度和练习统计")
def get_students(
    class_id: int = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    items, total = list_students(db, current_user.id, class_id, page, page_size)
    return paginated_success(items, total, page, page_size)


@router.get("/projects", summary="作品审核列表", description="教师端：按状态筛选所有学生作品，支持关键词搜索和分页")
def get_all_projects(
    status: str = None,
    keyword: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    projects, total = list_all_projects(
        db, status=status, page=page, page_size=page_size,
        teacher_id=current_user.id, keyword=keyword,
    )
    return paginated_success([format_project(db, p) for p in projects], total, page, page_size)


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
    current_user: AuthUser = Depends(require_role("teacher")),
):
    p = reject_project(db, project_id, data.reason or "")
    if not p:
        raise BusinessException(404, "作品不存在")
    return success()


def _sanitize_filename(name: str) -> str:
    """安全处理文件名，移除路径分隔符、控制字符等危险字符"""
    if not name:
        return "unnamed"
    # 移除路径分隔符、通配符和其他文件系统危险字符
    dangerous = r'\\/:*?"<>|'
    result = []
    for c in str(name):
        code = ord(c)
        # 过滤控制字符（<32，保留常用空白）和 DEL（127）
        if code < 32 or code == 127:
            continue
        if c in dangerous:
            continue
        result.append(c)
    safe = "".join(result).strip(". ")
    return safe if safe else "unnamed"


def _get_project_file_content(db: Session, p: Project) -> tuple[bytes | None, str | None]:
    """获取作品的报告文件内容和 ZIP 内文件名。

    优先通过 report_file_id（新方式）从存储适配器获取文件流；
    降级到 report_url（旧方式）从本地磁盘读取历史文件。

    返回 (content_bytes, inner_zip_name)，文件不存在时返回 (None, None)
    """
    author = db.query(User).filter(User.id == p.author_id).first()
    author_name = author.name if author else str(p.author_id)
    safe_title = _sanitize_filename(p.title)

    # 优先使用 report_file_id → 统一存储
    report_file_id = getattr(p, "report_file_id", None)
    if report_file_id:
        record, stream = resolve_file_stream(db, report_file_id)
        if record and stream:
            try:
                content = stream.read()
                ext = record.extension or Path(
                    record.original_name).suffix or ".pdf"
                inner_name = f"{author_name}_{safe_title}{ext}"
                return content, inner_name
            finally:
                stream.close()

    # 降级到 report_url → 本地历史文件
    report_url = getattr(p, "report_url", "")
    if report_url:
        filename = Path(report_url).name
        if filename:
            upload_dir = Path(settings.local_upload_dir)
            file_path = upload_dir / filename
            if file_path.exists() and file_path.is_file():
                content = file_path.read_bytes()
                ext = file_path.suffix or ".pdf"
                inner_name = f"{author_name}_{safe_title}{ext}"
                return content, inner_name

    return None, None


@router.get("/projects/batch-download", summary="批量下载作品报告", description="教师端：打包下载所有已通过作品的 PDF 报告为 ZIP 文件")
def batch_download_projects(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    # 查询已通过的作品（同时支持新 report_file_id 和旧 report_url）
    projects, _ = list_all_projects(db, "approved", teacher_id=current_user.id)
    projects = [
        p for p in projects
        if getattr(p, "report_file_id", None) or getattr(p, "report_url", "")
    ]

    if not projects:
        raise BusinessException(404, "没有可下载的作品报告")

    # 使用临时文件作为 ZIP 缓冲区（避免全部文件读入内存）
    tmp_path: str | None = None
    file_added = False

    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp_path = tmp.name
        tmp.close()  # 关闭文件句柄，保留磁盘文件

        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in projects:
                content, inner_name = _get_project_file_content(db, p)
                if content is None:
                    continue
                zf.writestr(inner_name, content)
                file_added = True

        if not file_added:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise BusinessException(404, "没有可下载的作品报告文件")

        # 流式输出：从临时文件分块读取，避免内存中持有完整 ZIP
        # 使用 BackgroundTasks 在响应发送完成后清理临时文件
        file_path = tmp_path

        def _cleanup():
            try:
                os.unlink(file_path)
            except OSError:
                pass

        background_tasks.add_task(_cleanup)

        f = open(file_path, "rb")

        def _chunk_reader():
            try:
                while True:
                    chunk = f.read(64 * 1024)  # 64KB 块
                    if not chunk:
                        break
                    yield chunk
            finally:
                f.close()

        today = datetime.now().strftime("%Y%m%d")
        filename = f"project_reports_{today}.zip"

        return StreamingResponse(
            _chunk_reader(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


# ──────────────────────────────────────────────────────────────
# 学生成绩 Excel 导出
# ──────────────────────────────────────────────────────────────

def _write_student_sheet(ws, students: list) -> None:
    """向工作表写入学生成绩：表头行、数据行、末尾汇总行"""
    # 表头行
    headers = ["序号", "学号", "姓名", "专业", "班级", "学习进度(%)", "练习题数", "正确率(%)"]
    ws.append(headers)

    # 数据行，每个学生一行
    for idx, s in enumerate(students, start=1):
        ws.append([
            idx,
            s["id"],
            s["name"],
            s["major"] or "",
            s["class_name"] or "未分班",
            s["progress"],
            s["exercises"],
            s["accuracy"],
        ])

    # 汇总行（仅当有数据时追加）
    if students:
        count = len(students)
        avg_progress = round(sum(s["progress"] for s in students) / count, 1)
        avg_exercises = round(sum(s["exercises"] for s in students) / count, 1)
        avg_accuracy = round(sum(s["accuracy"] for s in students) / count, 1)
        ws.append(["平均", "—", "—", "—", "—", avg_progress,
                  avg_exercises, avg_accuracy])


@router.get("/students/export", summary="导出学生成绩", description="教师端：将学生成绩导出为 Excel 文件，支持按班级筛选")
def export_students_excel(
    class_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    """导出学生成绩为 Excel。指定 class_id 时单 Sheet，否则全部班级多 Sheet"""
    # 复用现有 service 获取学生成绩（不分页，全量导出）
    students, _ = list_students(db, current_user.id, class_id=class_id)
    today = date.today().strftime("%Y-%m-%d")
    wb = Workbook()

    if class_id is not None:
        # 情况 A：指定班级——单 Sheet 导出
        # 优先从学生成绩获取班级名，兜底查数据库
        class_name = ""
        if students:
            class_name = students[0]["class_name"] or ""
        if not class_name:
            cls = db.query(Class).filter(Class.id == class_id).first()
            class_name = cls.name if cls else f"班级{class_id}"

        ws = wb.active
        ws.title = class_name[:31]  # openpyxl 限制 Sheet 名最长 31 字符
        _write_student_sheet(ws, students)

        filename = f"学生成绩_{class_name}_{today}.xlsx"
    else:
        # 情况 B：全部学生——多 Sheet 导出
        # Sheet 1：全部学生汇总
        ws_all = wb.active
        ws_all.title = "全部学生"
        _write_student_sheet(ws_all, students)

        # 按班级分组，无班级归入"未分班"
        class_groups: dict[str, list] = {}
        for s in students:
            cn = s["class_name"] or "未分班"
            if cn not in class_groups:
                class_groups[cn] = []
            class_groups[cn].append(s)

        # 每个班级一个 Sheet，同时收集摘要数据
        summary_rows = []
        for cn, group in class_groups.items():
            ws_cls = wb.create_sheet(title=cn[:31])
            _write_student_sheet(ws_cls, group)
            count = len(group)
            avg_p = round(sum(s["progress"]
                          for s in group) / count, 1) if count else 0.0
            avg_e = round(sum(s["exercises"]
                          for s in group) / count, 1) if count else 0.0
            avg_a = round(sum(s["accuracy"]
                          for s in group) / count, 1) if count else 0.0
            summary_rows.append([cn, count, avg_p, avg_e, avg_a])

        # 最后一个 Sheet：数据摘要（各班级汇总）
        ws_summary = wb.create_sheet(title="数据摘要")
        ws_summary.append(["班级名称", "学生人数", "平均学习进度(%)", "平均练习题数", "平均正确率(%)"])
        for row in summary_rows:
            ws_summary.append(row)

        filename = f"学生成绩_全部班级_{today}.xlsx"

    # 将工作簿写入内存缓冲区，避免落盘
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # RFC 5987 编码，支持中文文件名
    encoded_filename = quote(filename, encoding="utf-8")

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
