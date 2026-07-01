"""教师学生列表数据库分页测试。"""
from app.core.security import get_password_hash
from app.models.entities import Class, Course, StudentClassEnrollment, User
from tests.conftest import auth_header


def test_teacher_students_pagination_uses_unique_students(client, db_session, teacher_token):
    """分页返回不重复的学生 ID（同一学生在多个班级不应重复计算）。"""
    course = Course(name="分页课程", created_by="T001", is_public=False)
    db_session.add(course)
    db_session.flush()
    class_a = Class(name="A班", course_id=course.id, created_by="T001")
    class_b = Class(name="B班", course_id=course.id, created_by="T001")
    db_session.add_all([class_a, class_b])
    db_session.flush()
    for index in range(15):
        user = User(id=f"SX{index:03d}", name=f"学生{index:03d}", role="student", hashed_password=get_password_hash("abc123"))
        db_session.add(user)
        db_session.flush()
        db_session.add(StudentClassEnrollment(user_id=user.id, class_id=class_a.id, import_order=index))
    db_session.add(StudentClassEnrollment(user_id="SX000", class_id=class_b.id, import_order=99))
    db_session.commit()

    resp = client.get("/api/teacher/students?page=1&page_size=10", headers=auth_header(teacher_token))
    data = resp.json()

    assert data["code"] == 0
    assert data["data"]["total"] >= 15
    ids = [item["id"] for item in data["data"]["items"]]
    assert len(ids) == len(set(ids))


def test_teacher_students_keyword_is_case_insensitive(client, db_session, teacher_token):
    """关键词搜索应大小写不敏感。"""
    course = Course(name="搜索课程", created_by="T001", is_public=False)
    db_session.add(course)
    db_session.flush()
    class_ = Class(name="搜索班", course_id=course.id, created_by="T001")
    db_session.add(class_)
    db_session.flush()
    db_session.add(User(id="SCASE001", name="Alice Student", role="student", hashed_password=get_password_hash("abc123")))
    db_session.add(StudentClassEnrollment(user_id="SCASE001", class_id=class_.id, import_order=1))
    db_session.commit()

    resp = client.get("/api/teacher/students?keyword=alice", headers=auth_header(teacher_token))
    data = resp.json()

    assert data["code"] == 0
    assert any(item["id"] == "SCASE001" for item in data["data"]["items"])
