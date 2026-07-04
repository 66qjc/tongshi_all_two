"""资料文件鉴权和 Nginx 内部跳转测试"""
from pathlib import Path

from app.core.config import settings
from app.models.entities import Course, Material, StoredFile
from tests.conftest import auth_header


def _stored_file(db_session, created_by="T001", object_key="course/test.pdf", content_type="application/pdf"):
    stored = StoredFile(
        biz_type="material",
        storage_provider="local",
        bucket_name="",
        object_key=object_key,
        original_name="test.pdf",
        stored_name="test.pdf",
        content_type=content_type,
        extension=".pdf",
        size_bytes=1024,
        created_by=created_by,
    )
    db_session.add(stored)
    db_session.flush()
    return stored


def _write_local_file(object_key: str, content: bytes = b"test file"):
    target = Path(settings.local_upload_dir) / object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def _material(db_session, course_id=1, file_id=None, type_="pdf"):
    material = Material(
        course_id=course_id,
        type=type_,
        title="大文件资料",
        url=f"/api/files/{file_id}" if file_id else "",
        size="1 KB",
        file_id=file_id,
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)
    return material


def test_generic_file_rejects_anonymous_user(client, db_session):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)

    response = client.get(f"/api/files/{stored.id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data["code"] == 401


def test_generic_file_rejects_student_outside_material_course(client, db_session, student_token):
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    stored = _stored_file(db_session, created_by="T002", object_key="course/other.pdf")
    _write_local_file(stored.object_key)
    _material(db_session, course_id=other_course.id, file_id=stored.id)

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(student_token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data["code"] == 404


def test_generic_file_allows_enrolled_student_for_material(client, db_session, student_token):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    _material(db_session, file_id=stored.id)

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(student_token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_generic_file_allows_owner_teacher_for_material(client, db_session, teacher_token):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    _material(db_session, file_id=stored.id)

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(teacher_token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_generic_file_allows_when_any_material_reference_is_accessible(client, db_session, student_token):
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    stored = _stored_file(db_session, created_by="T002", object_key="course/shared.pdf")
    _write_local_file(stored.object_key)
    _material(db_session, course_id=other_course.id, file_id=stored.id)
    _material(db_session, course_id=1, file_id=stored.id)

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(student_token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_material_file_returns_x_accel_redirect_for_owner_teacher(client, db_session, teacher_token):
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(teacher_token))

    assert response.status_code == 200
    assert response.headers["x-accel-redirect"] == f"/_protected_uploads/{stored.object_key}"
    assert response.headers["content-type"].startswith("application/pdf")
    assert "inline" in response.headers["content-disposition"]


def test_material_file_allows_enrolled_student(client, db_session, student_token):
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(student_token))

    assert response.status_code == 200
    assert response.headers["x-accel-redirect"] == f"/_protected_uploads/{stored.object_key}"


def test_material_file_allows_query_token_for_browser_preview(client, db_session, student_token, monkeypatch):
    """资料预览通过 video/object 打开时只能携带 URL token。"""
    monkeypatch.setattr("app.core.config.settings.allow_query_token_for_files", True)
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file?token={student_token}")

    assert response.status_code == 200
    assert response.headers["x-accel-redirect"] == f"/_protected_uploads/{stored.object_key}"


def test_material_file_rejects_other_teacher(client, db_session, other_teacher_token):
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(other_teacher_token))
    data = response.json()

    assert data["code"] == 404


def test_material_file_rejects_student_not_in_course(client, db_session, student_token):
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    stored = _stored_file(db_session, created_by="T002", object_key="course/other.pdf")
    material = _material(db_session, course_id=other_course.id, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(student_token))
    data = response.json()

    assert data["code"] == 404


def test_material_file_rejects_path_traversal_object_key(client, db_session, teacher_token):
    stored = _stored_file(db_session, object_key="../secret.pdf")
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(teacher_token))
    data = response.json()

    assert data["code"] == 400


def test_course_contents_include_material_preview(client, db_session, student_token):
    from app.models.entities import MaterialPreview

    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)
    preview = MaterialPreview(
        material_id=material.id,
        status="ready",
        summary="这是一段资料摘要",
        page_count=12,
    )
    db_session.add(preview)
    db_session.commit()

    response = client.get("/api/courses/1/contents", headers=auth_header(student_token))
    data = response.json()

    assert data["code"] == 0
    target = next(item for item in data["data"] if item["id"] == material.id)
    assert target["preview"]["status"] == "ready"
    assert target["preview"]["summary"] == "这是一段资料摘要"
    assert target["preview"]["page_count"] == 12
