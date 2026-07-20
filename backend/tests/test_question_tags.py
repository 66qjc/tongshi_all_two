"""共享题库标签聚合接口测试。"""
from datetime import datetime, timezone

from app.models.entities import Question
from tests.conftest import auth_header


def _admin_token(client) -> str:
    resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    return resp.json()["data"]["access_token"]


def _create_active_question(db_session, *, stem: str, tags: list[str], created_by: str = "T001") -> Question:
    q = Question(
        type="fill",
        course_id=None,
        stem=stem,
        options=[],
        answer="答案",
        explanation="",
        tags=tags,
        created_by=created_by,
        star_rating=3,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    return q


def test_teacher_question_tags_are_deduped_sorted_and_ignore_soft_deleted(client, teacher_token, db_session):
    _create_active_question(db_session, stem="标签聚合活跃题1", tags=["深度学习", "机器学习", " 机器学习 "])
    _create_active_question(db_session, stem="标签聚合活跃题2", tags=["人工智能", "机器学习", ""])
    soft = _create_active_question(db_session, stem="标签聚合软删题", tags=["仅软删可见"])
    soft.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    resp = client.get("/api/questions/tags", headers=auth_header(teacher_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    tags = body["data"]
    assert tags == sorted(set(tags), key=lambda s: s.casefold())
    assert "机器学习" in tags
    assert "深度学习" in tags
    assert "人工智能" in tags
    assert "仅软删可见" not in tags
    # trim 后去重，不应出现带空格副本或空串
    assert all(tag.strip() == tag and tag for tag in tags)
    assert tags.count("机器学习") == 1


def test_admin_question_bank_tags_match_teacher_scope(client, db_session):
    admin_token = _admin_token(client)
    _create_active_question(db_session, stem="管理员标签聚合题", tags=["公共标签A", "公共标签B"])

    admin_resp = client.get("/api/admin/question-bank/tags", headers=auth_header(admin_token))
    assert admin_resp.status_code == 200, admin_resp.text
    admin_body = admin_resp.json()
    assert admin_body["code"] == 0
    assert "公共标签A" in admin_body["data"]
    assert "公共标签B" in admin_body["data"]

    teacher_login = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    assert teacher_login.status_code == 200, teacher_login.text
    teacher_token = teacher_login.json()["data"]["access_token"]
    teacher_resp = client.get("/api/questions/tags", headers=auth_header(teacher_token))
    assert teacher_resp.status_code == 200
    assert set(teacher_resp.json()["data"]) == set(admin_body["data"])


def test_question_tags_require_auth_roles(client, teacher_token):
    # 本项目业务鉴权多为 HTTP 200 + body.code 非 0
    anon = client.get("/api/questions/tags")
    assert anon.status_code == 200
    assert anon.json()["code"] in {401, 403}

    # 教师不能访问管理员标签接口
    teacher_on_admin = client.get(
        "/api/admin/question-bank/tags",
        headers=auth_header(teacher_token),
    )
    assert teacher_on_admin.status_code == 200
    assert teacher_on_admin.json()["code"] in {401, 403}
