"""学生端课程入口和错题本课程信息回归测试。"""

from app.core.security import get_password_hash
from app.models.entities import Course, Question, QuizAttempt, User
from tests.conftest import auth_header


def _login(client, user_id: str, password: str = "abc123") -> str:
    return client.post("/api/token", json={"id": user_id, "password": password}).json()["data"]["access_token"]


def test_student_course_list_only_returns_enrolled_courses(client, db_session, student_token):
    """学生课程列表不应展示未加入的公共课程。"""
    enrolled_course = db_session.query(Course).filter(Course.created_by == "T001").first()
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    other_course.is_public = True
    db_session.commit()

    resp = client.get("/api/courses", headers=auth_header(student_token)).json()

    assert resp["code"] == 0
    assert resp["data"]["hint"] is None
    ids = [item["id"] for item in resp["data"]["courses"]]
    assert ids == [enrolled_course.id]
    assert other_course.id not in ids


def test_student_without_class_gets_course_hint(client, db_session):
    """未加入班级的学生应看到明确提示。"""
    student = User(
        id="2025888",
        name="未入班学生",
        hashed_password=get_password_hash("abc123"),
        role="student",
        major="测试专业",
    )
    db_session.add(student)
    db_session.commit()
    token = _login(client, student.id)

    resp = client.get("/api/courses", headers=auth_header(token)).json()

    assert resp["code"] == 0
    assert resp["data"]["courses"] == []
    assert resp["data"]["hint"] == "你尚未加入任何班级，请联系老师"


def test_wrong_questions_include_course_name_and_type(client, db_session, student_token):
    """错题本应返回课程名和题型，供前端按课程分组展示。"""
    question = db_session.query(Question).filter(Question.course_id == 1).first()
    db_session.add(
        QuizAttempt(
            user_id="2025001",
            question_id=question.id,
            user_answer="A",
            is_correct=False,
        )
    )
    db_session.commit()

    resp = client.get("/api/profile/wrong-questions", headers=auth_header(student_token)).json()

    assert resp["code"] == 0
    assert len(resp["data"]) == 1
    item = resp["data"][0]
    assert item["course_id"] == question.course_id
    assert item["course_name"] == "测试课程"
    assert item["type"] == question.type


def test_student_cannot_access_other_course_detail(client, db_session, student_token):
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()

    for path in (
        f"/api/courses/{other_course.id}",
        f"/api/questions/courses/{other_course.id}",
    ):
        resp = client.get(path, headers=auth_header(student_token)).json()
        assert resp["code"] == 404
