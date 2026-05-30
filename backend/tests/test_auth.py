"""认证接口测试"""
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
        resp = client.post("/api/register", json={
            "id": "2025100", "name": "新学生", "password": "123456", "role": "student", "major": "测试"
        })
        # 纯数字密码触发 Pydantic 校验 → FastAPI 返回 422
        assert resp.status_code == 422

    def test_register_duplicate(self, client):
        resp = client.post("/api/register", json={
            "id": "2025001", "name": "重复", "password": "abc123", "role": "student", "major": "测试"
        })
        data = resp.json()
        assert data["code"] == 400
        assert "已注册" in data["message"]

    def test_get_me(self, client, student_token):
        resp = client.get("/api/me", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["id"] == "2025001"
        assert data["data"]["name"] == "测试学生"


class TestCourseContent:
    """课程内容接口测试"""

    def test_list_courses(self, client, student_token):
        resp = client.get("/api/questions/courses", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]) >= 1
        course = data["data"][0]
        assert course["name"] == "测试课程"
        assert "material_count" in course
        assert "question_count" in course

    def test_course_detail(self, client, student_token):
        resp = client.get("/api/questions/courses/1", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "测试课程"
        assert "class_count" in data["data"]

    def test_course_detail_not_found(self, client, student_token):
        resp = client.get("/api/questions/courses/99", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 404

    def test_create_question_requires_teacher(self, client, student_token):
        """学生无权新增题目"""
        resp = client.post("/api/questions",
                          json={"course_id": 1, "type": "choice", "stem": "测试", "options": [], "answer": "A"},
                          headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 403


class TestQuiz:
    """答题接口测试"""

    def test_submit_answer(self, client, student_token):
        resp = client.post("/api/quiz/submit",
                           json={"question_id": 1, "user_answer": "B"},
                           headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["is_correct"] is True
        assert "explanation" in data["data"]

    def test_submit_wrong_answer(self, client, student_token):
        resp = client.post("/api/quiz/submit",
                           json={"question_id": 1, "user_answer": "A"},
                           headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["is_correct"] is False

    def test_quiz_stats(self, client, student_token):
        # 先答一题
        client.post("/api/quiz/submit",
                    json={"question_id": 1, "user_answer": "B"},
                    headers=auth_header(student_token))
        resp = client.get("/api/quiz/stats", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["questions_done"] >= 1

    def test_quiz_history(self, client, student_token):
        resp = client.get("/api/quiz/history", headers=auth_header(student_token))
        data = resp.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)
