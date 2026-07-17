"""管理员独立共享题库测试。"""
from app.models.entities import Course, Question, QuestionContributionLog
from tests.conftest import auth_header


def _admin_token(client) -> str:
    resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    return resp.json()["data"]["access_token"]


def test_admin_question_bank_works_without_public_course(client, db_session):
    """没有任何活跃公共课程时，管理员仍可列表、新增空挂载题、编辑和软删除。"""
    admin_token = _admin_token(client)
    # 确保没有活跃公共课
    db_session.query(Course).filter(Course.is_public.is_(True)).update(
        {Course.deleted_at: Course.created_at},
        synchronize_session=False,
    )
    db_session.commit()

    listed = client.get("/api/admin/question-bank", headers=auth_header(admin_token)).json()
    assert listed["code"] == 0

    created = client.post(
        "/api/admin/question-bank",
        json={
            "type": "fill",
            "stem": "独立题库新增题",
            "options": [],
            "answer": "北京",
            "explanation": "",
            "tags": ["独立"],
            "star_rating": 4,
        },
        headers=auth_header(admin_token),
    ).json()
    assert created["code"] == 0
    question_id = created["data"]["id"]
    assert created["data"]["course_id"] is None
    assert created["data"]["mount_course_state"] in {"none", "purged"}

    updated = client.put(
        f"/api/admin/question-bank/{question_id}",
        json={
            "type": "fill",
            "stem": "独立题库编辑后",
            "options": [],
            "answer": "上海",
            "explanation": "更新",
            "tags": ["独立"],
            "star_rating": 5,
        },
        headers=auth_header(admin_token),
    ).json()
    assert updated["code"] == 0
    assert updated["data"]["stem"] == "独立题库编辑后"

    deleted = client.delete(
        f"/api/admin/question-bank/{question_id}",
        headers=auth_header(admin_token),
    ).json()
    assert deleted["code"] == 0
    row = db_session.get(Question, question_id)
    assert row is not None
    assert row.deleted_at is not None

    log = (
        db_session.query(QuestionContributionLog)
        .filter(QuestionContributionLog.public_course_name == "独立题库")
        .order_by(QuestionContributionLog.id.desc())
        .first()
    )
    assert log is not None
    assert log.public_course_id is None


def test_legacy_public_course_question_routes_have_deprecation_headers(client, db_session):
    """旧公共课题库路由仍可用，但必须返回弃用响应头。"""
    admin_token = _admin_token(client)
    public = Course(
        name="弃用头测试公共课",
        description="",
        created_by="admin",
        is_public=True,
    )
    db_session.add(public)
    db_session.commit()
    db_session.refresh(public)

    listed = client.get(
        f"/api/admin/public-courses/{public.id}/questions",
        headers=auth_header(admin_token),
    )
    assert listed.status_code == 200
    assert listed.headers.get("Deprecation") == "true"
    assert "/api/admin/question-bank" in (listed.headers.get("Link") or "")
    assert listed.json()["code"] == 0

    created = client.post(
        f"/api/admin/public-courses/{public.id}/questions",
        json={
            "type": "fill",
            "stem": "旧入口新增题",
            "options": [],
            "answer": "答案",
            "explanation": "",
            "tags": [],
            "star_rating": 3,
        },
        headers=auth_header(admin_token),
    )
    assert created.status_code == 200
    assert created.headers.get("Deprecation") == "true"
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["course_id"] == public.id
