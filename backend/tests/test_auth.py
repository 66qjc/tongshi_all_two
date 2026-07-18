"""认证接口测试"""

from datetime import datetime, timezone

import pytest
from jose import jwt

from app.core.config import Settings, settings
from app.core.exceptions import BusinessException
from app.models.entities import AuditLog, Question, User
from tests.conftest import auth_header


class TestAuth:
    """登录与鉴权"""

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

    def test_register_endpoint_removed(self, client):
        resp = client.post(
            "/api/register",
            json={
                "id": "2025100",
                "name": "新学生",
                "password": "abc123",
                "role": "student",
                "major": "测试",
            },
        )
        # 路由已删除：Starlette/FastAPI 返回 404
        assert resp.status_code == 404

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

    def test_file_access_token_contains_only_required_claims(self):
        from app.core.security import create_file_access_token

        issued_at = datetime.now(timezone.utc).timestamp()
        token = create_file_access_token("2025001", 7)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        assert set(payload) == {"sub", "scope", "file_id", "exp"}
        assert payload["sub"] == "2025001"
        assert payload["scope"] == "file_access"
        assert payload["file_id"] == 7
        assert 295 <= payload["exp"] - issued_at <= 305

    @pytest.mark.parametrize(
        "payload",
        [
            {"scope": "file_access", "file_id": 7, "exp": 4102444800},
            {"sub": "", "scope": "file_access", "file_id": 7, "exp": 4102444800},
            {"sub": 2025001, "scope": "file_access", "file_id": 7, "exp": 4102444800},
            {"sub": "2025001", "file_id": 7, "exp": 4102444800},
            {"sub": "2025001", "scope": "login", "file_id": 7, "exp": 4102444800},
            {"sub": "2025001", "scope": "file_access", "exp": 4102444800},
            {"sub": "2025001", "scope": "file_access", "file_id": "7", "exp": 4102444800},
            {"sub": "2025001", "scope": "file_access", "file_id": True, "exp": 4102444800},
            {"sub": "2025001", "scope": "file_access", "file_id": 8, "exp": 4102444800},
            {"sub": "2025001", "scope": "file_access", "file_id": 7},
            {"sub": "2025001", "scope": "file_access", "file_id": 7, "exp": "4102444800"},
            {"sub": "2025001", "scope": "file_access", "file_id": 7, "exp": 1},
        ],
        ids=[
            "missing-sub",
            "empty-sub",
            "wrong-sub-type",
            "missing-scope",
            "wrong-scope",
            "missing-file-id",
            "wrong-file-id-type",
            "boolean-file-id",
            "cross-file",
            "missing-exp",
            "wrong-exp-type",
            "expired",
        ],
    )
    def test_decode_file_access_token_rejects_invalid_claims(self, payload):
        from app.core.security import decode_file_access_token

        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

        with pytest.raises(BusinessException) as exc_info:
            decode_file_access_token(token, 7)

        assert exc_info.value.code == 401
        assert exc_info.value.message == "文件访问凭据无效或已过期"

    def test_decode_file_access_token_rejects_malformed_token(self):
        from app.core.security import decode_file_access_token

        with pytest.raises(BusinessException) as exc_info:
            decode_file_access_token("not-a-jwt", 7)

        assert exc_info.value.code == 401
        assert exc_info.value.message == "文件访问凭据无效或已过期"

    def test_file_access_token_cannot_call_regular_api(self, client):
        from app.core.security import create_file_access_token

        token = create_file_access_token("2025001", 7)
        response = client.get("/api/me", headers=auth_header(token)).json()

        assert response["code"] == 401

    def test_change_password_rotates_token_and_returns_replacement(self, client, db_session, student_token):
        response = client.put(
            "/api/change-password",
            json={"old_password": "abc123", "new_password": "NewPass123"},
            headers=auth_header(student_token),
        ).json()

        assert response["code"] == 0
        replacement_token = response["data"]["access_token"]
        assert replacement_token
        assert client.get("/api/me", headers=auth_header(student_token)).json()["code"] == 401
        assert client.get("/api/me", headers=auth_header(replacement_token)).json()["code"] == 0
        assert db_session.query(AuditLog).filter(
            AuditLog.user_id == "2025001",
            AuditLog.action == "user.password_change",
        ).count() == 1

    def test_security_answer_reset_invalidates_existing_token(self, client, db_session, student_token):
        configured = client.put(
            "/api/security-questions",
            json={"questions": [{"question": "测试问题", "answer": "测试答案"}]},
            headers=auth_header(student_token),
        ).json()
        question_id = configured["data"][0]["id"]

        reset = client.post(
            "/api/password/forgot/reset",
            json={
                "user_id": "2025001",
                "answers": [{"question_id": question_id, "answer": "测试答案"}],
                "new_password": "ResetPass123",
            },
        ).json()

        assert reset["code"] == 0
        assert client.get("/api/me", headers=auth_header(student_token)).json()["code"] == 401
        assert db_session.query(AuditLog).filter(
            AuditLog.user_id == "2025001",
            AuditLog.action == "user.password_reset",
        ).count() == 1

    def test_soft_deleted_user_cannot_login_or_reuse_token(self, client, db_session, student_token):
        user = db_session.query(User).filter(User.id == "2025001").one()
        user.deleted_at = datetime.now(timezone.utc)
        user.deleted_by = "admin"
        db_session.commit()

        login = client.post("/api/token", json={"id": "2025001", "password": "abc123"}).json()
        current = client.get("/api/me", headers=auth_header(student_token)).json()

        assert login["code"] == 401
        assert current["code"] == 401

    def test_settings_require_secret_key(self, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)

        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings()

    def test_settings_instances_do_not_reuse_previous_secret_key(self, monkeypatch):
        """连续实例不得复用前一次测试设置的密钥。"""
        monkeypatch.setenv("SECRET_KEY", "first-secret-key")
        first = Settings()

        monkeypatch.setenv("SECRET_KEY", "second-secret-key")
        second = Settings()

        assert first.secret_key == "first-secret-key"
        assert second.secret_key == "second-secret-key"

    def test_legacy_query_token_setting_is_ignored(self, monkeypatch):
        monkeypatch.setenv("ALLOW_QUERY_TOKEN_FOR_FILES", "true")

        runtime_settings = Settings()

        assert not hasattr(runtime_settings, "allow_query_token_for_files")

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
