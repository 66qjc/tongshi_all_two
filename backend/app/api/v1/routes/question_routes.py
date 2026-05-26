"""Question routes"""
from __future__ import annotations

from io import BytesIO

from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.core.upload_validation import validate_upload, ALLOWED_EXCEL_EXTENSIONS, MAX_EXCEL_SIZE
from app.schemas.common import AuthUser, QuestionCreate, QuestionUpdate, CourseCreateRequest, CourseUpdateRequest
from app.services.chapter_service import format_chapters
from app.services.question_service import (
    list_questions, create_question, update_question, delete_question,
    get_chapter_questions, list_courses, create_course, update_course, delete_course,
    get_course_detail, import_questions_from_excel,
)

router = APIRouter(prefix="/questions", tags=["questions"])


def _format_question(q):
    return {
        "id": q.id,
        "type": q.type,
        "chapter_id": q.chapter_id,
        "chapter_name": q.chapter.title if q.chapter else "",
        "course_id": q.chapter.course_id if q.chapter else None,
        "course_name": q.chapter.course.name if q.chapter and q.chapter.course else "",
        "stem": q.stem,
        "options": q.options or [],
        "answer": q.answer,
        "explanation": q.explanation or "",
    }


@router.get("", summary="题目列表", description="按章节、题型、课程筛选题目")
def get_questions(
    chapter_id: Optional[int] = None,
    type: Optional[str] = None,
    course_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    questions = list_questions(db, chapter_id, type, course_id)
    return success([_format_question(q) for q in questions])


@router.get("/chapter/{chapter_id}", summary="章节题目", description="获取指定章节的所有题目（用于测验）")
def get_chapter_questions_for_quiz(chapter_id: int, db: Session = Depends(get_db), _: AuthUser = Depends(get_current_user)):
    questions = get_chapter_questions(db, chapter_id)
    return success([_format_question(q) for q in questions])


@router.post("", summary="新增题目", description="教师端：创建选择题或填空题")
def add_question(data: QuestionCreate, db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    q = create_question(db, data.model_dump())
    return success({"id": q.id})


@router.put("/{question_id}", summary="编辑题目", description="教师端：修改指定题目的内容")
def edit_question(question_id: int, data: QuestionUpdate, db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    q = update_question(db, question_id, data.model_dump(exclude_unset=True))
    if not q:
        raise BusinessException(404, "题目不存在")
    return success()


@router.delete("/{question_id}", summary="删除题目", description="教师端：删除指定题目")
def remove_question(question_id: int, db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    if not delete_question(db, question_id):
        raise BusinessException(404, "题目不存在")
    return success()


@router.get("/courses", summary="课程列表", description="获取所有课程")
def get_courses(db: Session = Depends(get_db), _: AuthUser = Depends(get_current_user)):
    return success([{
        "id": c.id,
        "name": c.name,
        "created_at": c.created_at.isoformat() if c.created_at else "",
        "chapter_count": len(c.chapters),
        "material_count": sum(len(ch.materials) for ch in c.chapters),
    } for c in list_courses(db)])


@router.post("/courses", summary="创建课程", description="教师端：创建新课程")
def add_course(data: CourseCreateRequest, db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    course = create_course(db, data.name.strip())
    return success({"id": course.id})


@router.get("/courses/{course_id}", summary="课程详情", description="返回课程信息、章节列表和资料统计")
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    detail = get_course_detail(db, course_id)
    if not detail:
        raise BusinessException(404, "课程不存在")
    course, chapters, material_count = detail
    return success({
        "id": course.id,
        "name": course.name,
        "created_at": course.created_at.isoformat() if course.created_at else "",
        "chapter_count": len(chapters),
        "material_count": material_count,
        "chapters": format_chapters(db, chapters, current_user.id),
    })


@router.put("/courses/{course_id}", summary="修改课程名称", description="教师端：修改指定课程的名称")
def edit_course(course_id: int, data: CourseUpdateRequest, db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    course = update_course(db, course_id, data.name.strip())
    if not course:
        raise BusinessException(404, "课程不存在")
    return success()


@router.delete("/courses/{course_id}", summary="删除课程", description="教师端：删除指定课程")
def remove_course(course_id: int, db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    if not delete_course(db, course_id):
        raise BusinessException(404, "课程不存在")
    return success()


@router.post("/import", summary="Excel 批量导入题目", description="教师端：上传 Excel 批量导入题目（.xlsx，表头：type/chapter/stem/options/answer/explanation）")
def import_questions(file: UploadFile = File(...), db: Session = Depends(get_db), _: AuthUser = Depends(require_role("teacher"))):
    content = file.file.read()
    err = validate_upload(file.filename, len(
        content), allowed_extensions=ALLOWED_EXCEL_EXTENSIONS, max_size=MAX_EXCEL_SIZE)
    if err:
        raise BusinessException(400, err)
    wb = load_workbook(filename=BytesIO(content), data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value is not None else "" for c in next(
        ws.iter_rows(min_row=1, max_row=1))]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        item = {headers[i]: row[i] if i < len(
            row) else None for i in range(len(headers))}
        rows.append(item)
    return success(import_questions_from_excel(db, rows))
