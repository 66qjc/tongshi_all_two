"""Class routes"""
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.core.upload_validation import validate_upload, ALLOWED_EXCEL_EXTENSIONS, MAX_EXCEL_SIZE
from app.schemas.common import AuthUser, ClassCreate, ClassEnrollRequest
from app.services.class_service import (
    list_classes, create_class, delete_class,
    list_class_students, enroll_student, remove_student,
    import_students_from_excel,
)

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("", summary="班级列表", description="教师端：返回当前教师课程下的班级及其学生人数")
def get_classes(
    course_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    return success(list_classes(db, current_user.id, course_id, keyword))


@router.post("", summary="创建班级", description="教师端：创建新班级")
def post_class(data: ClassCreate, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    cls = create_class(db, data.name, data.course_id, current_user.id)
    return success({"id": cls.id})


@router.delete("/{class_id}", summary="删除班级", description="教师端：删除班级及所有注册关系")
def remove_class(class_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    cls = delete_class(db, class_id, current_user.id)
    if not cls:
        raise BusinessException(404, "班级不存在")
    return success()


@router.get("/{class_id}/students", summary="班级学生列表", description="教师端：返回指定班级的所有学生")
def get_students(class_id: int, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    students = list_class_students(db, class_id, current_user.id)
    if students is None:
        raise BusinessException(404, "班级不存在")
    return success(students)


@router.post("/{class_id}/enroll", summary="添加学生", description="教师端：将学生手动添加到班级；学号不存在时若提供姓名则自动建号")
def add_student(class_id: int, data: ClassEnrollRequest, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    enrollment, status = enroll_student(
        db, class_id, data.student_id, current_user.id, data.name)
    return success({"status": status})


@router.delete("/{class_id}/enroll/{student_id}", summary="移除学生", description="教师端：从班级中移除指定学生")
def remove_enrollment(class_id: int, student_id: str, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_role("teacher"))):
    enrollment = remove_student(db, class_id, student_id, current_user.id)
    if not enrollment:
        raise BusinessException(404, "选课关系不存在")
    return success()


@router.post("/import", summary="Excel 批量导入", description="教师端：上传 Excel 文件批量导入学生（自动识别学号/姓名/专业列），可指定 class_id 自动注册到班级")
def import_class_students(
    file: UploadFile = File(...),
    class_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    content = file.file.read()
    err = validate_upload(file.filename, len(
        content), allowed_extensions=ALLOWED_EXCEL_EXTENSIONS, max_size=MAX_EXCEL_SIZE)
    if err:
        raise BusinessException(400, err)
    result = import_students_from_excel(db, content, current_user.id, class_id=class_id)
    return success(result)
