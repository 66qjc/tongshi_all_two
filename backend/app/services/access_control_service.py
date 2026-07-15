"""访问权限辅助服务。"""

from sqlalchemy.orm import Session

from app.models.entities import Class, Course, StudentClassEnrollment


def student_can_access_course(db: Session, user_id: str, course_id: int) -> bool:
    """判断学生是否加入了课程对应的任一活跃班级。

    仅统计未软删的班级与课程；软删后旧选课关系不再授予访问权。
    """
    return db.query(StudentClassEnrollment.id).join(
        Class,
        Class.id == StudentClassEnrollment.class_id,
    ).join(
        Course,
        Course.id == Class.course_id,
    ).filter(
        StudentClassEnrollment.user_id == user_id,
        Class.course_id == course_id,
        Class.deleted_at.is_(None),
        Course.deleted_at.is_(None),
        Course.id == course_id,
    ).first() is not None


def student_has_active_course_enrollment(db: Session, user_id: str) -> bool:
    """判断学生是否至少加入了一个未软删课程下的活跃班级。"""
    return db.query(StudentClassEnrollment.id).join(
        Class,
        Class.id == StudentClassEnrollment.class_id,
    ).join(
        Course,
        Course.id == Class.course_id,
    ).filter(
        StudentClassEnrollment.user_id == user_id,
        Class.deleted_at.is_(None),
        Course.deleted_at.is_(None),
        Class.course_id.isnot(None),
    ).first() is not None
