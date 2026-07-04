"""认证接口测试"""

import pytest

from app.core.config import Settings
from app.models.entities import Question, User
from tests.conftest import auth_header


class TestAuth:
    """登录和注册"""

    def test_login_success(self, client):
        resp = client.post("/api/token", json={"id": "2025001", "password": "abc123"})
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 0
        assert "access_token" in data["data"]
        assert data["data"]["user"]["role"] == "student"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/token", json={"id": "2025001", "password": "wrong"})
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/token", json={"id": "9999999", "password": "abc123"})
        data = resp.json()
        assert data["code"] == 401

    def test_register_too_simple_password(self, client):
        resp = client.post(
            "/api/register",
            json={
                "id": "2025100",
                "name": "新学生",
                "password": "123456",
                "role": "student",
                "major": "测试",
            },
        )
        assert resp.status_code == 422

    def test_register_duplicate(self, client):
        resp = client.post(
            "/api/register",
            json={
                "id": "2025001",
                "name": "重复",
                "password": "abc123",
                "role": "student",
                "major": "测试",
            },
        )
        data = resp.json()
        assert data["code"] == 400
        assert "已注册" in data["message"]

    def test_register_rejects_teacher_role(self, client):
        resp = client.post(
            "/api/register",
            json={
                "id": "T9001",
                "name": "公开注册教师",
                "password": "abc123456",
                "role": "teacher",
                "major": "",
            },
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 400
        assert "角色" in data["message"]

    def test_register_rejects_admin_role(self, client):
        resp = client.post(
            "/api/register",
            json={
                "id": "A9001",
                "name": "恶意管理员",
                "password": "abc123456",
                "role": "admin",
                "major": "",
            },
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 400
        assert "角色" in data["message"]

    def test_register_rejects_unknown_role(self, client):
        resp = client.post(
            "/api/register",
            json={
                "id": "X9001",
                "name": "未知角色",
                "password": "abc123456",
                "role": "superadmin",
                "major": "",
            },
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 400
        assert "角色" in data["message"]

    def test_get_me(self, client, student_token):
        resp = client.get("/api/me", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["id"] == "2025001"
        assert data["data"]["name"] == "测试学生"

    def test_get_me_rejects_query_token(self, client, student_token):
        resp = client.get(f"/api/me?token={student_token}")
        data = resp.json()
        assert resp.status_code == 200
        assert data["code"] == 401

    def test_settings_require_secret_key(self, monkeypatch):
        original_init = Settings.__init__

        def init_without_secret(self):
            self.secret_key = ""
            self.algorithm = "HS256"
            self.access_token_expire_minutes = 10080
            self.allowed_origins = "*"
            self.database_url = "sqlite://"
            self.allow_query_token_for_files = False
            original_init(self)

        monkeypatch.setattr(Settings, "__init__", init_without_secret)

        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings()

    def test_seed_data_does_not_create_default_admin(self, db_session):
        from seed_data import seed

        db_session.query(User).filter(User.id == "admin").delete()
        db_session.commit()

        seed()

        admin = db_session.query(User).filter(User.id == "admin").first()
        assert admin is None


class TestCourseContent:
    """课程内容接口测试"""

    def test_list_courses(self, client, student_token):
        resp = client.get("/api/courses", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]["courses"]) >= 1
        course = data["data"]["courses"][0]
        assert course["name"] == "测试课程"
        assert "material_count" in course
        assert "question_count" in course

    def test_course_detail(self, client, student_token):
        resp = client.get("/api/courses/1", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "测试课程"
        assert "class_count" in data["data"]

    def test_course_detail_not_found(self, client, student_token):
        resp = client.get("/api/courses/99", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 404

    def test_create_question_requires_teacher(self, client, student_token):
        """学生无权新增题目"""
        resp = client.post(
            "/api/questions",
            json={"course_id": 1, "type": "choice", "stem": "测试", "options": [], "answer": "A"},
            headers=auth_header(student_token),
        )
        data = resp.json()
        assert data["code"] == 403


class TestQuiz:
    """答题接口测试"""

    def test_submit_answer(self, client, student_token):
        resp = client.post(
            "/api/quiz/submit",
            json={"question_id": 1, "user_answer": "B"},
            headers=auth_header(student_token),
        )
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["is_correct"] is True
        assert "explanation" in data["data"]

    def test_submit_wrong_answer(self, client, student_token):
        resp = client.post(
            "/api/quiz/submit",
            json={"question_id": 1, "user_answer": "A"},
            headers=auth_header(student_token),
        )
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["is_correct"] is False

    def test_submit_multi_choice_answer_ignores_order(self, client, db_session, student_token):
        """多选题答案按字母集合判定，不受提交顺序影响。"""
        question = Question(
            type="multi_choice",
            course_id=1,
            stem="以下哪些是编程语言？",
            options=["A. Python", "B. Java", "C. HTML", "D. C++"],
            answer="ABD",
            explanation="HTML 是标记语言。",
        )
        db_session.add(question)
        db_session.commit()

        resp = client.post(
            "/api/quiz/submit",
            json={"question_id": question.id, "user_answer": "DBA"},
            headers=auth_header(student_token),
        )
        data = resp.json()

        assert data["code"] == 0
        assert data["data"]["is_correct"] is True

    def test_quiz_stats(self, client, student_token):
        client.post(
            "/api/quiz/submit",
            json={"question_id": 1, "user_answer": "B"},
            headers=auth_header(student_token),
        )
        resp = client.get("/api/quiz/stats", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["questions_done"] >= 1

    def test_quiz_history(self, client, student_token):
        resp = client.get("/api/quiz/history", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)
