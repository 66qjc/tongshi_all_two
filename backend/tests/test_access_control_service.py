"""课程访问权限服务测试。"""

from datetime import datetime, timezone

from app.models.entities import Class, Course
from app.services.access_control_service import (
    student_can_access_course,
    student_has_active_course_enrollment,
)


def test_student_can_access_joined_course(db_session):
    assert student_can_access_course(db_session, "2025001", 1) is True


def test_student_cannot_access_unjoined_course(db_session):
    assert student_can_access_course(db_session, "2025001", 2) is False


def test_student_cannot_access_soft_deleted_joined_course(db_session):
    course = db_session.query(Course).filter(Course.id == 1).first()
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert student_can_access_course(db_session, "2025001", 1) is False


def test_student_cannot_access_course_when_class_soft_deleted(db_session):
    cls = db_session.query(Class).filter(Class.course_id == 1).first()
    cls.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert student_can_access_course(db_session, "2025001", 1) is False


def test_student_has_active_course_enrollment(db_session):
    assert student_has_active_course_enrollment(db_session, "2025001") is True
    course = db_session.query(Course).filter(Course.id == 1).first()
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert student_has_active_course_enrollment(db_session, "2025001") is False
