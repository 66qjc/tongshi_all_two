"""Class service"""
from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Tuple

from openpyxl import load_workbook
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.security import get_password_hash
from app.models.entities import (
    Announcement,
    AnnouncementRead,
    Class,
    Project,
    ProjectLike,
    QuizAttempt,
    StudentClassEnrollment,
    StudentProgress,
    TaskCompletion,
    User,
)

logger = logging.getLogger(__name__)

DEFAULT_STUDENT_PASSWORD = "123456"


def _now_iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def list_classes(db: Session):
    classes = db.query(Class).order_by(Class.created_at.desc(), Class.id.desc()).all()
    result = []
    for cls in classes:
        student_count = db.query(StudentClassEnrollment).filter(StudentClassEnrollment.class_id == cls.id).count()
        result.append({
            "id": cls.id,
            "name": cls.name,
            "major": cls.major,
            "student_count": student_count,
            "created_at": _now_iso(cls.created_at),
        })
    return result


def create_class(db: Session, name: str, major: str):
    existing = db.query(Class).filter(Class.name == name, Class.major == major).first()
    if existing:
        raise BusinessException(400, "班级已存在")
    cls = Class(name=name, major=major)
    try:
        db.add(cls)
        db.commit()
        db.refresh(cls)
        logger.info(f"班级创建: id={cls.id}, name={name}, major={major}")
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "创建班级失败")
    return cls


def _delete_student_data(db: Session, student_id: str):
    project_ids = [row.id for row in db.query(Project.id).filter(Project.author_id == student_id).all()]
    if project_ids:
        db.query(ProjectLike).filter(ProjectLike.project_id.in_(project_ids)).delete(synchronize_session=False)
    db.query(ProjectLike).filter(ProjectLike.user_id == student_id).delete(synchronize_session=False)
    db.query(Project).filter(Project.author_id == student_id).delete(synchronize_session=False)
    db.query(QuizAttempt).filter(QuizAttempt.user_id == student_id).delete(synchronize_session=False)
    db.query(StudentProgress).filter(StudentProgress.user_id == student_id).delete(synchronize_session=False)
    db.query(AnnouncementRead).filter(AnnouncementRead.user_id == student_id).delete(synchronize_session=False)
    db.query(TaskCompletion).filter(TaskCompletion.user_id == student_id).delete(synchronize_session=False)
    db.query(StudentClassEnrollment).filter(StudentClassEnrollment.user_id == student_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == student_id, User.role == "student").delete(synchronize_session=False)


def delete_class(db: Session, class_id: int):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        return None
    try:
        student_ids = [
            row.user_id
            for row in db.query(StudentClassEnrollment.user_id)
            .filter(StudentClassEnrollment.class_id == class_id)
            .all()
        ]
        for student_id in student_ids:
            other_class_count = (
                db.query(StudentClassEnrollment)
                .filter(
                    StudentClassEnrollment.user_id == student_id,
                    StudentClassEnrollment.class_id != class_id,
                )
                .count()
            )
            if other_class_count > 0:
                db.query(StudentClassEnrollment).filter(
                    StudentClassEnrollment.user_id == student_id,
                    StudentClassEnrollment.class_id == class_id,
                ).delete(synchronize_session=False)
            else:
                _delete_student_data(db, student_id)

        class_announcement_ids = [
            row.id for row in db.query(Announcement.id).filter(Announcement.class_id == class_id).all()
        ]
        if class_announcement_ids:
            db.query(AnnouncementRead).filter(
                AnnouncementRead.announcement_id.in_(class_announcement_ids)
            ).delete(synchronize_session=False)
            db.query(TaskCompletion).filter(
                TaskCompletion.announcement_id.in_(class_announcement_ids)
            ).delete(synchronize_session=False)
        db.query(Announcement).filter(Announcement.class_id == class_id).delete(synchronize_session=False)
        db.delete(cls)
        db.commit()
        logger.info(f"班级删除: class_id={class_id}, name={cls.name}")
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "删除班级失败")
    return cls


def list_class_students(db: Session, class_id: int):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        return None
    enrollments = (
        db.query(StudentClassEnrollment)
        .filter(StudentClassEnrollment.class_id == class_id)
        .order_by(StudentClassEnrollment.enrolled_at.desc())
        .all()
    )
    result = []
    for enrollment in enrollments:
        student = db.query(User).filter(User.id == enrollment.user_id).first()
        if not student:
            continue
        result.append({
            "id": student.id,
            "name": student.name,
            "major": student.major or "",
            "enrolled_at": _now_iso(enrollment.enrolled_at),
        })
    return result


def enroll_student(db: Session, class_id: int, student_id: str):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        return None, "班级不存在"
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        return None, "学生不存在"
    if student.role != "student":
        raise BusinessException(400, "仅可添加学生账号")
    existing = db.query(StudentClassEnrollment).filter(
        StudentClassEnrollment.class_id == class_id,
        StudentClassEnrollment.user_id == student_id,
    ).first()
    if existing:
        return existing, "已存在"
    enrollment = StudentClassEnrollment(user_id=student_id, class_id=class_id)
    try:
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "添加学生失败")
    return enrollment, "created"


def remove_student(db: Session, class_id: int, student_id: str):
    enrollment = db.query(StudentClassEnrollment).filter(
        StudentClassEnrollment.class_id == class_id,
        StudentClassEnrollment.user_id == student_id,
    ).first()
    if not enrollment:
        return None
    try:
        db.delete(enrollment)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "移除学生失败")
    return enrollment


def _split_row(row: dict) -> Tuple[str, str, str, str]:
    return (
        str(row.get("student_id", "")).strip(),
        str(row.get("name", "")).strip(),
        str(row.get("major", "")).strip(),
        str(row.get("class_name", "")).strip(),
    )


def import_students_from_excel(db: Session, file_bytes: bytes):
    try:
        wb = load_workbook(filename=BytesIO(file_bytes), data_only=True)
        ws = wb.active
    except Exception:
        raise BusinessException(400, "Excel 文件解析失败")

    headers = [str(cell.value).strip() if cell.value is not None else "" for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    required = {"student_id", "name", "major", "class_name"}
    if not required.issubset(set(headers)):
        raise BusinessException(400, "Excel 表头不完整")

    header_map = {h: idx for idx, h in enumerate(headers)}
    result = {"success_count": 0, "skip_count": 0, "fail_count": 0, "errors": []}

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        row_data = {
            "student_id": row[header_map["student_id"]] if header_map["student_id"] < len(row) else None,
            "name": row[header_map["name"]] if header_map["name"] < len(row) else None,
            "major": row[header_map["major"]] if header_map["major"] < len(row) else None,
            "class_name": row[header_map["class_name"]] if header_map["class_name"] < len(row) else None,
        }
        student_id, name, major, class_name = _split_row(row_data)
        if not student_id or not name or not major or not class_name:
            result["fail_count"] += 1
            result["errors"].append({"row": row_idx, "reason": "字段不能为空"})
            continue

        # 使用保存点让每行独立提交，单行失败不影响其他行
        try:
            with db.begin_nested():
                student = db.query(User).filter(User.id == student_id).first()
                if not student:
                    student = User(
                        id=student_id,
                        name=name,
                        hashed_password=get_password_hash(DEFAULT_STUDENT_PASSWORD),
                        role="student",
                        major=major,
                    )
                    db.add(student)
                    db.flush()
                else:
                    student.name = name
                    student.major = major

                cls = db.query(Class).filter(Class.name == class_name).first()
                if not cls:
                    cls = Class(name=class_name, major=major)
                    db.add(cls)
                    db.flush()

                existing = db.query(StudentClassEnrollment).filter(
                    StudentClassEnrollment.user_id == student_id,
                    StudentClassEnrollment.class_id == cls.id,
                ).first()
                if existing:
                    result["skip_count"] += 1
                    continue

                db.add(StudentClassEnrollment(user_id=student_id, class_id=cls.id))
            result["success_count"] += 1
        except (SQLAlchemyError, IntegrityError) as exc:
            result["fail_count"] += 1
            result["errors"].append({"row": row_idx, "reason": str(exc)[:120]})
            continue

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException(500, "批量导入失败")
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "批量导入失败")

    return result
