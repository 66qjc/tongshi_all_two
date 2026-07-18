"""游客可见性与学生删除作品相关回归测试。"""

from app.models.entities import Course, Project
from tests.conftest import auth_header


def _create_project(client, token: str, course_id: int, title: str = "学生作品") -> int:
    resp = client.post(
        "/api/projects",
        json={
            "course_id": course_id,
            "title": title,
            "description": "作品说明",
            "tags": ["AI"],
            "image_urls": [],
            "image_file_ids": [],
        },
        headers=auth_header(token),
    ).json()
    assert resp["code"] == 0
    return resp["data"]["id"]


def test_student_can_delete_own_pending_project(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    project_id = _create_project(client, student_token, course.id, "待审可删")

    resp = client.delete(
        f"/api/projects/{project_id}",
        headers=auth_header(student_token),
    ).json()
    project = db_session.query(Project).filter(Project.id == project_id).one()

    assert resp["code"] == 0
    assert project.deleted_at is not None
    assert project.deleted_by == "2025001"


def test_student_can_delete_own_rejected_project(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    project = Project(
        title="驳回可删",
        author_id="2025001",
        course_id=course.id,
        description="被驳回作品",
        status="rejected",
        reject_reason="需修改",
    )
    db_session.add(project)
    db_session.commit()

    resp = client.delete(
        f"/api/projects/{project.id}",
        headers=auth_header(student_token),
    ).json()
    db_session.refresh(project)

    assert resp["code"] == 0
    assert project.deleted_at is not None
    assert project.deleted_by == "2025001"


def test_student_cannot_delete_approved_project(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    project = Project(
        title="已通过不可删",
        author_id="2025001",
        course_id=course.id,
        description="已通过作品",
        status="approved",
    )
    db_session.add(project)
    db_session.commit()

    resp = client.delete(
        f"/api/projects/{project.id}",
        headers=auth_header(student_token),
    ).json()
    db_session.refresh(project)

    assert resp["code"] == 400
    assert "已通过" in resp["message"]
    assert project.deleted_at is None


def test_student_cannot_delete_others_project(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    project = Project(
        title="他人作品",
        author_id="2025002",
        course_id=course.id,
        description="其它学生作品",
        status="pending",
    )
    db_session.add(project)
    db_session.commit()

    resp = client.delete(
        f"/api/projects/{project.id}",
        headers=auth_header(student_token),
    ).json()
    db_session.refresh(project)

    assert resp["code"] in (403, 404)
    assert project.deleted_at is None


def test_guest_can_list_only_approved_projects(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    pending_id = _create_project(client, student_token, course.id, "待审隐藏")
    approved = Project(
        title="公开作品",
        author_id="2025001",
        description="x",
        status="approved",
    )
    db_session.add(approved)
    db_session.commit()

    resp = client.get("/api/projects?page=1&page_size=50").json()
    assert resp["code"] == 0
    ids = [item["id"] for item in resp["data"]["items"]]
    assert approved.id in ids
    assert pending_id not in ids


def test_guest_can_view_approved_detail_but_not_pending(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    pending_id = _create_project(client, student_token, course.id, "待审详情")
    approved = Project(
        title="公开详情",
        author_id="2025001",
        description="x",
        status="approved",
    )
    db_session.add(approved)
    db_session.commit()

    ok = client.get(f"/api/projects/{approved.id}").json()
    assert ok["code"] == 0
    assert ok["data"]["title"] == "公开详情"
    assert ok["data"].get("is_liked") is False

    denied = client.get(f"/api/projects/{pending_id}").json()
    assert denied["code"] == 404


def test_guest_like_increments_counter_only(client, db_session):
    approved = Project(
        title="可赞作品",
        author_id="2025001",
        description="x",
        status="approved",
        likes=3,
    )
    db_session.add(approved)
    db_session.commit()

    resp = client.post(f"/api/projects/{approved.id}/guest-like").json()
    assert resp["code"] == 0
    assert resp["data"]["liked"] is True
    assert resp["data"]["likes"] == 4

    from app.models.entities import ProjectLike
    assert db_session.query(ProjectLike).filter(ProjectLike.project_id == approved.id).count() == 0


def test_guest_like_rejects_non_approved(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    pending_id = _create_project(client, student_token, course.id, "不可赞")
    resp = client.post(f"/api/projects/{pending_id}/guest-like").json()
    assert resp["code"] in (400, 404)
