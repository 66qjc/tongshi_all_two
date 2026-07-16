"""公开学习馆游客访问测试。"""
from fastapi.testclient import TestClient

from app.models.entities import Course, CourseStage, Material, StoredFile


def test_guest_can_list_public_courses_only(client: TestClient, db_session):
    public_course = Course(name="公开 AI 通识", created_by="admin", is_public=True, description="面向所有学习者")
    private_course = Course(name="教师私有课程", created_by="T001", is_public=False, description="内部课程")
    db_session.add_all([public_course, private_course])
    db_session.flush()
    db_session.add_all([
        Material(course_id=public_course.id, type="pdf", title="公开资料", url="/uploads/open.pdf", size="1 MB"),
        Material(course_id=private_course.id, type="pdf", title="私有资料", url="/uploads/private.pdf", size="1 MB"),
    ])
    db_session.commit()

    resp = client.get("/api/public/learning/courses")
    assert resp.status_code == 200
    data = resp.json()["data"]
    names = [item["name"] for item in data["courses"]]
    assert "公开 AI 通识" in names
    assert "教师私有课程" not in names
    course = next(item for item in data["courses"] if item["name"] == "公开 AI 通识")
    assert "lesson_count" not in course
    assert course["material_count"] == 1


def test_guest_can_read_public_course_detail_and_stage_materials(client: TestClient, db_session):
    course = Course(name="公开课程详情", created_by="admin", is_public=True, description="公开说明")
    db_session.add(course)
    db_session.flush()
    stage = CourseStage(course_id=course.id, name="第一阶段", sort_order=1)
    db_session.add(stage)
    db_session.flush()
    db_session.add_all([
        Material(course_id=course.id, stage_id=stage.id, type="pdf", title="阶段资料", url="/uploads/stage.pdf", size="2 MB"),
    ])
    db_session.commit()

    detail_resp = client.get(f"/api/public/learning/courses/{course.id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["name"] == "公开课程详情"
    assert "lesson_count" not in detail
    assert detail["stages"][0]["materials"][0]["title"] == "阶段资料"


def test_guest_cannot_read_private_course_or_private_materials(client: TestClient, db_session):
    private_course = Course(name="私有课程", created_by="T001", is_public=False)
    db_session.add(private_course)
    db_session.flush()
    db_session.add_all([
        Material(course_id=private_course.id, type="pdf", title="私有资料", url="/uploads/private.pdf", size="1 MB"),
    ])
    db_session.commit()

    detail_resp = client.get(f"/api/public/learning/courses/{private_course.id}")
    materials_resp = client.get("/api/public/learning/materials")

    assert detail_resp.status_code == 200
    assert detail_resp.json()["code"] == 404
    assert all(item["title"] != "私有资料" for item in materials_resp.json()["data"]["items"])


def test_guest_can_preview_public_material_file_only(client: TestClient, db_session):
    public_course = Course(name="公开文件课程", created_by="admin", is_public=True)
    private_course = Course(name="私有文件课程", created_by="T001", is_public=False)
    db_session.add_all([public_course, private_course])
    db_session.flush()
    public_file = StoredFile(
        biz_type="material",
        biz_id=public_course.id,
        storage_provider="local",
        object_key="materials/public.pdf",
        original_name="public.pdf",
        stored_name="public.pdf",
        content_type="application/pdf",
        size_bytes=128,
        created_by="admin",
    )
    private_file = StoredFile(
        biz_type="material",
        biz_id=private_course.id,
        storage_provider="local",
        object_key="materials/private.pdf",
        original_name="private.pdf",
        stored_name="private.pdf",
        content_type="application/pdf",
        size_bytes=128,
        created_by="T001",
    )
    db_session.add_all([public_file, private_file])
    db_session.flush()
    public_material = Material(course_id=public_course.id, type="pdf", title="公开文件", file_id=public_file.id, size="128 B")
    private_material = Material(course_id=private_course.id, type="pdf", title="私有文件", file_id=private_file.id, size="128 B")
    db_session.add_all([public_material, private_material])
    db_session.commit()

    public_resp = client.get(f"/api/public/learning/materials/{public_material.id}/file")
    private_resp = client.get(f"/api/public/learning/materials/{private_material.id}/file")

    assert public_resp.status_code == 200
    assert public_resp.headers["x-accel-redirect"] == "/_protected_uploads/materials/public.pdf"
    assert public_resp.headers["content-disposition"].startswith("inline;")
    assert "content-length" not in public_resp.headers
    assert private_resp.status_code == 200
    assert private_resp.json()["code"] == 404
