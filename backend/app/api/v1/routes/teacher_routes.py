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
from app.schemas.common import AuthUser, ProjectReviewAction, ResetRequestResolve
from app.services.teacher_service import (
    build_student_task_score_export,
    get_teacher_stats,
    list_all_projects,
    list_students,
)
from app.services.project_service import approve_project, reject_project, delete_project, format_project, batch_load_liked_set
from app.services.class_service import remove_students_from_teacher_classes
from app.services.file_service import resolve_file_stream
from app.services.auth_service import (
    get_reset_requests_for_teacher,
    approve_reset_request_for_teacher,
    reject_reset_request_for_teacher,
)
from app.models.entities import User, Project, Class
from openpyxl import Workbook

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/stats", summary="工作台概览", description="教师端：返回总学生数、我的课程数、待审核作品数、练习题量等教学数据")
def teacher_stats(db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    return success(get_teacher_stats(db, current_user.id))


@router.get("/students", summary="学生成绩", description="教师端：返回所有学生的学号、姓名、专业、班级、学习进度和练习统计")
def get_students(
    class_id: int = None,
    course_id: int = None,
    keyword: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    items, total = list_students(
        db,
        current_user.id,
        class_id=class_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        course_id=course_id,
    )
    return paginated_success(items, total, page, page_size)


@router.post("/students/batch-delete", summary="批量移出学生", description="教师端：将学生从当前教师管理的班级中移出，不删除学生账号")
def batch_delete_students(
    student_ids: list[str],
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    if not student_ids:
        raise BusinessException(400, "请选择要移出的学生")

    try:
        deleted_count, failed_ids = remove_students_from_teacher_classes(db, current_user.id, student_ids)
        db.commit()
    except Exception:
        db.rollback()
        raise BusinessException(500, "批量移出失败")

    return success({
        "deleted_count": deleted_count,
        "failed_ids": failed_ids,
    })


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
    liked = batch_load_liked_set(db, [p.id for p in projects], current_user.id)
    return paginated_success([format_project(db, p, current_user.id, liked_set=liked) for p in projects], total, page, page_size)


@router.post("/projects/{project_id}/approve", summary="通过作品审核", description="教师端：将指定作品设为审核通过")
def approve(project_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    p = approve_project(db, project_id, current_user.id)
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
    p = reject_project(db, project_id, data.reason or "", current_user.id)
    if not p:
        raise BusinessException(404, "作品不存在")
    return success()


@router.delete("/projects/{project_id}", summary="删除作品", description="教师端：删除指定作品及其所有关联数据")
def remove_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    p = delete_project(db, project_id, current_user.id)
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
    # 表头行（与前端表格列保持一致）
    headers = ["序号", "学号", "姓名", "专业", "班级", "已完成", "未完成", "完成率(%)"]
    ws.append(headers)

    # 数据行，每个学生一行
    for idx, s in enumerate(students, start=1):
        ws.append([
            s.get("serial_no") or idx,
            s["id"],
            s["name"],
            s["major"] or "",
            s["class_name"] or "未分班",
            s["completed_tasks"],
            s["incomplete_tasks"],
            s["task_completion_rate"],
        ])

    # 汇总行（仅当有数据时追加）
    if students:
        count = len(students)
        avg_completed = round(sum(s["completed_tasks"] for s in students) / count, 1)
        avg_incomplete = round(sum(s["incomplete_tasks"] for s in students) / count, 1)
        avg_rate = round(sum(s["task_completion_rate"] for s in students) / count, 1)
        ws.append(["平均", "—", "—", "—", "—", avg_completed,
                  avg_incomplete, avg_rate])


def _safe_sheet_title(name: str, used_titles: set[str]) -> str:
    """生成 Excel 可用且不重复的工作表名称。"""
    unsafe = set(r'[]:*?/\\')
    base = "".join(c for c in str(name or "未命名") if c not in unsafe).strip() or "未命名"
    base = base[:31]
    title = base
    index = 2
    while title in used_titles:
        suffix = f"_{index}"
        title = f"{base[:31 - len(suffix)]}{suffix}"
        index += 1
    used_titles.add(title)
    return title


def _write_overview_sheet(ws, course_groups: list[dict]) -> None:
    """写入按课程汇总的总览 Sheet。"""
    ws.append(["课程名称", "学生人数", "作业数", "平均已完成", "平均未完成", "平均完成率(%)"])
    for group in course_groups:
        students = group.get("students", [])
        count = len(students)
        avg_completed = round(sum(s["completed_tasks"] for s in students) / count, 1) if count else 0
        avg_incomplete = round(sum(s["incomplete_tasks"] for s in students) / count, 1) if count else 0
        avg_rate = round(sum(s["task_completion_rate"] for s in students) / count, 1) if count else 0
        ws.append([
            group.get("course_name") or "未命名课程",
            count,
            len(group.get("tasks", [])),
            avg_completed,
            avg_incomplete,
            avg_rate,
        ])


def _write_course_score_sheet(ws, group: dict) -> None:
    """写入单个课程下学生每次作业分数。"""
    tasks = group.get("tasks", [])
    students = group.get("students", [])
    base_headers = ["序号", "学号", "姓名", "专业", "班级", "已完成", "未完成", "完成率(%)"]
    ws.append(base_headers + [task["title"] for task in tasks])

    for idx, student in enumerate(students, start=1):
        scores = student.get("scores", {})
        ws.append([
            student.get("serial_no") or idx,
            student["id"],
            student["name"],
            student.get("major") or "",
            student.get("class_name") or "未分班",
            student["completed_tasks"],
            student["incomplete_tasks"],
            student["task_completion_rate"],
            *[scores.get(task["id"]) for task in tasks],
        ])

    if students:
        count = len(students)
        summary = [
            "平均",
            "—",
            "—",
            "—",
            "—",
            round(sum(s["completed_tasks"] for s in students) / count, 1),
            round(sum(s["incomplete_tasks"] for s in students) / count, 1),
            round(sum(s["task_completion_rate"] for s in students) / count, 1),
        ]
        for task in tasks:
            numeric_scores = [
                student.get("scores", {}).get(task["id"])
                for student in students
                if student.get("scores", {}).get(task["id"]) is not None
            ]
            summary.append(round(sum(numeric_scores) / len(numeric_scores), 1) if numeric_scores else "")
        ws.append(summary)


@router.get("/students/export", summary="导出学生成绩", description="教师端：将学生成绩导出为 Excel 文件，支持按班级筛选")
def export_students_excel(
    class_id: Optional[int] = None,
    course_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    """导出学生成绩为 Excel。按课程拆分 Sheet，并横向展示每次作业分数。"""
    today = date.today().strftime("%Y-%m-%d")
    wb = Workbook()
    used_titles: set[str] = set()
    course_groups = build_student_task_score_export(
        db,
        current_user.id,
        course_id=course_id,
        class_id=class_id,
    )

    if course_id is not None or class_id is not None:
        # 指定课程或班级时，导出最窄范围对应的课程成绩表。
        group = course_groups[0] if course_groups else {
            "course_name": "学生成绩",
            "tasks": [],
            "students": [],
        }
        ws = wb.active
        ws.title = _safe_sheet_title(group.get("course_name") or "学生成绩", used_titles)
        _write_course_score_sheet(ws, group)

        scope_name = group.get("course_name") or "学生成绩"
        if class_id is not None:
            cls = db.query(Class).filter(Class.id == class_id).first()
            if cls:
                scope_name = cls.name
        filename = f"学生成绩_{scope_name}_{today}.xlsx"
    else:
        # 全量导出时，先写总览，再按课程拆分 Sheet。
        ws_overview = wb.active
        ws_overview.title = _safe_sheet_title("总览", used_titles)
        _write_overview_sheet(ws_overview, course_groups)
        for group in course_groups:
            ws_course = wb.create_sheet(title=_safe_sheet_title(group.get("course_name") or "未命名课程", used_titles))
            _write_course_score_sheet(ws_course, group)

        filename = f"学生成绩_全部课程_{today}.xlsx"

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


# ── 密码重置申请管理 ────────────────────────────────────────────────────

@router.get("/password-reset-requests", summary="获取密码重置申请", description="教师：查看本班学生的密码重置申请，可选 status 筛选（pending/approved/rejected）")
def list_reset_requests(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    return success(get_reset_requests_for_teacher(db, current_user.id, status))


@router.post("/password-reset-requests/{request_id}/approve", summary="审批密码重置", description="教师：审批通过本班学生的密码重置申请")
def approve_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    return success(approve_reset_request_for_teacher(db, request_id, current_user.id))


@router.post("/password-reset-requests/{request_id}/reject", summary="驳回密码重置", description="教师：驳回本班学生的密码重置申请")
def reject_request(
    request_id: int,
    data: ResetRequestResolve,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    return success(reject_reset_request_for_teacher(db, request_id, current_user.id, data.reason))
