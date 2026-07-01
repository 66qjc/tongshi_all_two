"""课程分页服务测试。"""
from app.models.entities import Course
from tests.conftest import auth_header


def test_teacher_courses_page_filters_owned_in_database(client, db_session, teacher_token):
    """owned 分支应在数据库层按 created_by 过滤，并返回正确分页。"""
    for index in range(25):
        db_session.add(Course(name=f"owned-{index:02d}", created_by="T001", is_public=False))
    db_session.add(Course(name="public-visible", created_by="admin", is_public=True))
    db_session.commit()

    resp = client.get(
        "/api/courses?scope=owned&page=2&page_size=10",
        headers=auth_header(teacher_token),
    )
    data = resp.json()

    assert data["code"] == 0
    assert data["data"]["total"] >= 25
    assert len(data["data"]["items"]) == 10
    assert all(item["is_owner"] for item in data["data"]["items"])


def test_teacher_courses_page_filters_public_keyword(client, db_session, teacher_token):
    """public 分支应排除自己创建的课程，并支持关键词数据库过滤。"""
    db_session.add(Course(name="Public Alpha", created_by="admin", is_public=True))
    db_session.add(Course(name="Public Beta", created_by="admin", is_public=True))
    db_session.add(Course(name="Owned Alpha", created_by="T001", is_public=False))
    db_session.commit()

    resp = client.get(
        "/api/courses?scope=public&keyword=alpha&page=1&page_size=20",
        headers=auth_header(teacher_token),
    )
    data = resp.json()

    assert data["code"] == 0
    names = [item["name"] for item in data["data"]["items"]]
    assert "Public Alpha" in names
    assert "Owned Alpha" not in names
