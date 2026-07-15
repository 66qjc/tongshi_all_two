"""资料文件鉴权和 Nginx 内部跳转测试"""
import asyncio
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.requests import Request

from app.api.v1.routes import file_routes
from app.core.config import settings
from app.models.entities import (
    Course,
    Material,
    MaterialPreview,
    Project,
    ShowcaseItem,
    ShowcaseItemImage,
    StoredFile,
    StudentClassEnrollment,
    User,
)
from app.services import file_service
from tests.conftest import auth_header


def _stored_file(
    db_session,
    created_by="T001",
    object_key="course/test.pdf",
    content_type="application/pdf",
    size_bytes=1024,
    biz_type="material",
):
    stored = StoredFile(
        biz_type=biz_type,
        storage_provider="local",
        bucket_name="",
        object_key=object_key,
        original_name="test.pdf",
        stored_name="test.pdf",
        content_type=content_type,
        extension=".pdf",
        size_bytes=size_bytes,
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


def _request_access_url(client, file_id: int, token: str) -> str:
    response = client.post(f"/api/files/{file_id}/access-url", headers=auth_header(token))
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["expires_in"] == 300
    assert data["data"]["url"].startswith(f"/api/files/{file_id}?access_token=")
    return data["data"]["url"]


def _admin_token(client) -> str:
    response = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    data = response.json()
    assert data["code"] == 0
    return data["data"]["access_token"]


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


def test_generic_material_read_does_not_scan_showcase_content_blocks(
    client,
    db_session,
    teacher_token,
    monkeypatch,
):
    """已有资料关联时，读取不应扫描展示内容块 JSON。"""
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    _material(db_session, file_id=stored.id)
    scan_calls = []

    def record_showcase_content_scan(*args, **kwargs):
        scan_calls.append((args, kwargs))
        return False

    monkeypatch.setattr(
        file_service,
        "_showcase_content_block_file_exists",
        record_showcase_content_scan,
    )

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(teacher_token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert scan_calls == []


def test_generic_file_allows_when_any_material_reference_is_accessible(client, db_session, student_token):
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    stored = _stored_file(db_session, created_by="T002", object_key="course/shared.pdf")
    _write_local_file(stored.object_key)
    _material(db_session, course_id=other_course.id, file_id=stored.id)
    _material(db_session, course_id=1, file_id=stored.id)

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(student_token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_authorized_student_can_request_file_access_url_and_read_range(client, db_session, student_token):
    content = b"%PDF-1.4 signed file content"
    stored = _stored_file(db_session, size_bytes=len(content))
    _write_local_file(stored.object_key, content)
    _material(db_session, file_id=stored.id)

    signed_url = _request_access_url(client, stored.id, student_token)
    response = client.get(signed_url, headers={"Range": "bytes=0-15"})

    assert response.status_code == 206
    assert response.content == content[:16]
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == f"bytes 0-15/{len(content)}"
    assert response.headers["content-length"] == "16"


def test_descending_range_falls_back_to_full_response(client, db_session, student_token):
    content = b"0123456789abcdef"
    stored = _stored_file(db_session, size_bytes=len(content))
    _write_local_file(stored.object_key, content)
    _material(db_session, file_id=stored.id)
    signed_url = _request_access_url(client, stored.id, student_token)

    response = client.get(signed_url, headers={"Range": "bytes=10-5"})

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-length"] == str(len(content))
    assert "content-range" not in response.headers


def test_full_file_response_closes_underlying_stream(
    client,
    db_session,
    student_token,
    monkeypatch,
):
    content = b"full response stream"
    stored = _stored_file(db_session, size_bytes=len(content))
    _material(db_session, file_id=stored.id)

    class TrackingStream(BytesIO):
        def __init__(self, initial_bytes: bytes):
            super().__init__(initial_bytes)
            self.close_calls = 0

        def close(self):
            self.close_calls += 1
            super().close()

    stream = TrackingStream(content)
    monkeypatch.setattr(file_service._local_adapter, "exists", lambda **kwargs: True)
    monkeypatch.setattr(file_service._local_adapter, "open_stream", lambda **kwargs: stream)

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(student_token))

    assert response.status_code == 200
    assert response.content == content
    assert stream.closed is True
    assert stream.close_calls == 1


def test_full_file_response_closes_underlying_stream_on_client_disconnect(
    db_session,
    monkeypatch,
):
    content = b"x" * (64 * 1024 * 4)
    stored = _stored_file(db_session, size_bytes=len(content))
    _material(db_session, file_id=stored.id)

    class TrackingStream(BytesIO):
        def __init__(self, initial_bytes: bytes):
            super().__init__(initial_bytes)
            self.close_calls = 0

        def close(self):
            self.close_calls += 1
            super().close()

    stream = TrackingStream(content)
    monkeypatch.setattr(file_service._local_adapter, "exists", lambda **kwargs: True)
    monkeypatch.setattr(file_service._local_adapter, "open_stream", lambda **kwargs: stream)

    retained_iterators = []
    original_read_stream = file_routes._read_stream

    def retain_read_stream(source):
        iterator = original_read_stream(source)
        retained_iterators.append(iterator)
        return iterator

    # 保留同步生成器引用，避免 CPython 引用计数替响应层掩盖资源泄漏。
    monkeypatch.setattr(file_routes, "_read_stream", retain_read_stream)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": f"/api/files/{stored.id}",
        "raw_path": f"/api/files/{stored.id}".encode(),
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }
    request = Request(scope)
    current_user = file_routes.AuthUser(
        id="2025001",
        name="测试学生",
        role="student",
        major=None,
    )
    response = file_routes.get_file(stored.id, request, db_session, current_user)
    sent_messages = []

    async def drive_response_until_disconnect():
        first_body_sent = asyncio.Event()

        async def send(message):
            sent_messages.append(message)
            if message["type"] == "http.response.body" and message.get("body"):
                first_body_sent.set()
                await asyncio.sleep(0)

        async def receive():
            await first_body_sent.wait()
            return {"type": "http.disconnect"}

        await response(scope, receive, send)

    asyncio.run(drive_response_until_disconnect())

    assert retained_iterators
    assert any(
        message["type"] == "http.response.body" and message.get("body")
        for message in sent_messages
    )
    assert stream.closed is True
    assert stream.close_calls == 1


def test_anonymous_user_cannot_request_file_access_url(client, db_session):
    stored = _stored_file(db_session)
    _material(db_session, file_id=stored.id)

    response = client.post(f"/api/files/{stored.id}/access-url").json()

    assert response["code"] == 401


def test_student_outside_course_cannot_request_file_access_url(client, db_session, student_token):
    other_course = db_session.query(Course).filter(Course.created_by == "T002").one()
    stored = _stored_file(db_session, created_by="T002", object_key="course/private.pdf")
    _material(db_session, course_id=other_course.id, file_id=stored.id)

    response = client.post(
        f"/api/files/{stored.id}/access-url",
        headers=auth_header(student_token),
    ).json()

    assert response["code"] == 404


def test_login_token_query_parameters_are_rejected_for_file(client, db_session, student_token):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    _material(db_session, file_id=stored.id)

    legacy_query = client.get(f"/api/files/{stored.id}?token={student_token}").json()
    access_token_query = client.get(f"/api/files/{stored.id}?access_token={student_token}").json()

    assert legacy_query["code"] == 401
    assert access_token_query["code"] == 401


def test_file_access_token_cannot_be_reused_for_another_file(client, db_session, student_token):
    first = _stored_file(db_session, object_key="course/first.pdf")
    second = _stored_file(db_session, object_key="course/second.pdf")
    _material(db_session, file_id=first.id)
    _material(db_session, file_id=second.id)

    signed_url = _request_access_url(client, first.id, student_token)
    token = parse_qs(urlsplit(signed_url).query)["access_token"][0]
    response = client.get(f"/api/files/{second.id}?access_token={token}").json()

    assert response["code"] == 401


def test_file_access_token_rechecks_soft_deleted_user(client, db_session, student_token):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    _material(db_session, file_id=stored.id)
    signed_url = _request_access_url(client, stored.id, student_token)

    user = db_session.query(User).filter(User.id == "2025001").one()
    user.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.get(signed_url).json()

    assert response["code"] == 401


def test_file_access_token_rechecks_revoked_enrollment(client, db_session, student_token):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    _material(db_session, file_id=stored.id)
    signed_url = _request_access_url(client, stored.id, student_token)

    db_session.query(StudentClassEnrollment).filter(
        StudentClassEnrollment.user_id == "2025001",
    ).delete(synchronize_session=False)
    db_session.commit()

    response = client.get(signed_url).json()

    assert response["code"] == 404


def test_file_access_token_rejects_inactive_stored_file(client, db_session, student_token):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    _material(db_session, file_id=stored.id)
    signed_url = _request_access_url(client, stored.id, student_token)

    stored.status = "inactive"
    db_session.commit()

    response = client.get(signed_url).json()

    assert response["code"] == 404


def test_file_access_token_rechecks_soft_deleted_material_and_course(client, db_session, student_token):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    material = _material(db_session, file_id=stored.id)
    signed_url = _request_access_url(client, stored.id, student_token)

    material.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert client.get(signed_url).json()["code"] == 404

    material.deleted_at = None
    material.course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert client.get(signed_url).json()["code"] == 404


def test_file_access_token_rechecks_soft_deleted_project(client, db_session, student_token):
    stored = _stored_file(
        db_session,
        created_by="T001",
        object_key="project/report.pdf",
        biz_type="project",
    )
    _write_local_file(stored.object_key)
    project = Project(
        title="待删除作品",
        author_id="2025001",
        course_id=1,
        description="测试",
        tags=[],
        status="pending",
        report_file_id=stored.id,
    )
    db_session.add(project)
    db_session.commit()
    signed_url = _request_access_url(client, stored.id, student_token)

    project.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.get(signed_url).json()

    assert response["code"] == 404


def test_file_access_token_keeps_working_with_another_active_material_reference(client, db_session, student_token):
    stored = _stored_file(db_session)
    content = b"shared material"
    stored.size_bytes = len(content)
    _write_local_file(stored.object_key, content)
    deleted_material = _material(db_session, file_id=stored.id)
    _material(db_session, file_id=stored.id)
    signed_url = _request_access_url(client, stored.id, student_token)

    deleted_material.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.get(signed_url)

    assert response.status_code == 200
    assert response.content == content


def test_anonymous_user_can_read_active_showcase_image(client, db_session):
    content = b"public showcase image"
    stored = _stored_file(
        db_session,
        object_key="showcase/public.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    db_session.add(ShowcaseItem(
        section="welfare",
        title="公开展示",
        cover_file_id=stored.id,
        is_active=True,
        created_by="T001",
    ))
    db_session.commit()

    response = client.get(f"/api/files/{stored.id}")

    assert response.status_code == 200
    assert response.content == content


def test_anonymous_user_can_read_active_showcase_gallery_image(client, db_session):
    """匿名用户可以读取已激活展示的图库图片。"""
    content = b"public showcase gallery"
    stored = _stored_file(
        db_session,
        object_key="showcase/public-gallery.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    item = ShowcaseItem(
        section="welfare",
        title="公开图库",
        is_active=True,
        created_by="T001",
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(ShowcaseItemImage(showcase_item_id=item.id, file_id=stored.id))
    db_session.commit()

    response = client.get(f"/api/files/{stored.id}")

    assert response.status_code == 200
    assert response.content == content


def test_anonymous_user_can_read_active_showcase_content_block_image(client, db_session):
    content = b"public content block image"
    stored = _stored_file(
        db_session,
        object_key="showcase/content-block.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    db_session.add(ShowcaseItem(
        section="welfare",
        title="公开图文",
        content_blocks=[{"type": "image", "data": {"file_id": stored.id}}],
        is_active=True,
        created_by="T001",
    ))
    db_session.commit()

    response = client.get(f"/api/files/{stored.id}")

    assert response.status_code == 200
    assert response.content == content


def test_anonymous_user_cannot_read_inactive_showcase_content_block_image(client, db_session):
    content = b"inactive content block image"
    stored = _stored_file(
        db_session,
        object_key="showcase/inactive-content-block.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    db_session.add(ShowcaseItem(
        section="welfare",
        title="未展示图文",
        content_blocks=[{"type": "image", "data": {"file_id": stored.id}}],
        is_active=False,
        created_by="T001",
    ))
    db_session.commit()

    response = client.get(f"/api/files/{stored.id}")

    assert response.status_code == 200
    assert response.json()["code"] == 401


def test_inactive_showcase_cover_is_only_readable_by_owner(
    client,
    db_session,
    teacher_token,
    other_teacher_token,
):
    """未发布展示封面仅允许管理员或教师拥有者读取。"""
    content = b"inactive showcase cover"
    stored = _stored_file(
        db_session,
        object_key="showcase/inactive-cover.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    db_session.add(ShowcaseItem(
        section="welfare",
        title="未发布封面",
        cover_file_id=stored.id,
        is_active=False,
        created_by="T001",
    ))
    db_session.commit()

    owner_response = client.get(f"/api/files/{stored.id}", headers=auth_header(teacher_token))
    assert owner_response.status_code == 200
    assert owner_response.content == content
    other_response = client.get(f"/api/files/{stored.id}", headers=auth_header(other_teacher_token))
    assert other_response.json()["code"] == 404


def test_inactive_showcase_gallery_image_is_only_readable_by_owner(
    client,
    db_session,
    teacher_token,
    other_teacher_token,
):
    """未发布展示图库图片仅允许管理员或教师拥有者读取。"""
    content = b"inactive showcase gallery"
    stored = _stored_file(
        db_session,
        object_key="showcase/inactive-gallery.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    item = ShowcaseItem(
        section="welfare",
        title="未发布图库",
        is_active=False,
        created_by="T001",
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(ShowcaseItemImage(showcase_item_id=item.id, file_id=stored.id))
    db_session.commit()

    owner_response = client.get(f"/api/files/{stored.id}", headers=auth_header(teacher_token))
    assert owner_response.status_code == 200
    assert owner_response.content == content
    other_response = client.get(f"/api/files/{stored.id}", headers=auth_header(other_teacher_token))
    assert other_response.json()["code"] == 404


def test_inactive_showcase_content_block_image_is_only_readable_by_owner(
    client,
    db_session,
    teacher_token,
    other_teacher_token,
):
    """未发布展示内容块图片仅允许管理员或教师拥有者读取。"""
    content = b"inactive showcase content block"
    stored = _stored_file(
        db_session,
        object_key="showcase/inactive-owner-content-block.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    db_session.add(ShowcaseItem(
        section="welfare",
        title="未发布内容块",
        content_blocks=[{"type": "image", "data": {"file_id": stored.id}}],
        is_active=False,
        created_by="T001",
    ))
    db_session.commit()

    owner_response = client.get(f"/api/files/{stored.id}", headers=auth_header(teacher_token))
    assert owner_response.status_code == 200
    assert owner_response.content == content
    other_response = client.get(f"/api/files/{stored.id}", headers=auth_header(other_teacher_token))
    assert other_response.json()["code"] == 404


def test_admin_creator_can_read_inactive_showcase_content_block_image(client, db_session):
    """管理员创建者可以读取未激活展示内容块图片。"""
    content = b"inactive admin showcase content block"
    stored = _stored_file(
        db_session,
        created_by="admin",
        object_key="showcase/inactive-admin-content-block.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    db_session.add(ShowcaseItem(
        section="welfare",
        title="管理员未发布内容块",
        content_blocks=[{"type": "image", "data": {"file_id": stored.id}}],
        is_active=False,
        created_by="admin",
    ))
    db_session.commit()

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(_admin_token(client)))

    assert response.status_code == 200
    assert response.content == content


def test_admin_creator_can_read_inactive_showcase_cover_image(client, db_session):
    """管理员创建者可以读取未激活展示封面。"""
    content = b"inactive admin showcase cover"
    stored = _stored_file(
        db_session,
        created_by="admin",
        object_key="showcase/inactive-admin-cover.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    db_session.add(ShowcaseItem(
        section="welfare",
        title="管理员未发布封面",
        cover_file_id=stored.id,
        is_active=False,
        created_by="admin",
    ))
    db_session.commit()

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(_admin_token(client)))

    assert response.status_code == 200
    assert response.content == content


def test_admin_creator_can_read_inactive_showcase_gallery_image(client, db_session):
    """管理员创建者可以读取未激活展示图库图片。"""
    content = b"inactive admin showcase gallery"
    stored = _stored_file(
        db_session,
        created_by="admin",
        object_key="showcase/inactive-admin-gallery.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    item = ShowcaseItem(
        section="welfare",
        title="管理员未发布图库",
        is_active=False,
        created_by="admin",
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(ShowcaseItemImage(showcase_item_id=item.id, file_id=stored.id))
    db_session.commit()

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(_admin_token(client)))

    assert response.status_code == 200
    assert response.content == content


@pytest.mark.parametrize("reference_type", ["cover", "gallery", "content_block"])
def test_other_admin_cannot_read_inactive_showcase_file(
    client,
    db_session,
    reference_type,
):
    """非创建者管理员不能读取未激活展示文件。"""
    content = f"inactive showcase {reference_type}".encode()
    stored = _stored_file(
        db_session,
        object_key=f"showcase/inactive-other-admin-{reference_type}.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="showcase",
    )
    _write_local_file(stored.object_key, content)
    item = ShowcaseItem(
        section="welfare",
        title="教师未发布展示",
        is_active=False,
        created_by="T001",
    )
    if reference_type == "cover":
        item.cover_file_id = stored.id
    elif reference_type == "content_block":
        item.content_blocks = [{"type": "image", "data": {"file_id": stored.id}}]
    db_session.add(item)
    db_session.flush()
    if reference_type == "gallery":
        db_session.add(ShowcaseItemImage(showcase_item_id=item.id, file_id=stored.id))
    db_session.commit()

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(_admin_token(client)))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["code"] == 404


def test_anonymous_public_material_cover_rechecks_soft_delete(client, db_session):
    content = b"public course cover"
    stored = _stored_file(
        db_session,
        object_key="course/public-cover.jpg",
        content_type="image/jpeg",
        size_bytes=len(content),
        biz_type="material_preview",
    )
    _write_local_file(stored.object_key, content)
    course = Course(name="公开课程", created_by="T001", is_public=True)
    db_session.add(course)
    db_session.flush()
    material = Material(course_id=course.id, type="pdf", title="公开资料", file_id=None)
    db_session.add(material)
    db_session.flush()
    db_session.add(MaterialPreview(
        material_id=material.id,
        status="ready",
        cover_file_id=stored.id,
    ))
    db_session.commit()

    response = client.get(f"/api/files/{stored.id}")
    assert response.status_code == 200
    assert response.content == content

    material.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert client.get(f"/api/files/{stored.id}").json()["code"] == 401

    material.deleted_at = None
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert client.get(f"/api/files/{stored.id}").json()["code"] == 401


def test_material_file_returns_x_accel_redirect_for_owner_teacher(client, db_session, teacher_token):
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(teacher_token))

    assert response.status_code == 200
    assert response.headers["x-accel-redirect"] == f"/_protected_uploads/{stored.object_key}"
    assert response.headers["content-type"].startswith("application/pdf")
    assert "inline" in response.headers["content-disposition"]


def test_material_file_rejects_soft_deleted_material(client, db_session, teacher_token):
    """资料专用读取接口不得继续打开已软删除资料。"""
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)
    material.deleted_at = datetime.now(timezone.utc)
    material.deleted_by = "T001"
    db_session.commit()

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(teacher_token))

    assert response.json()["code"] == 404


def test_material_file_allows_enrolled_student(client, db_session, student_token):
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file", headers=auth_header(student_token))

    assert response.status_code == 200
    assert response.headers["x-accel-redirect"] == f"/_protected_uploads/{stored.object_key}"


def test_material_file_rejects_login_token_query_parameter(client, db_session, student_token):
    """资料专用接口也不得继续接受普通登录 Token 查询参数。"""
    stored = _stored_file(db_session)
    material = _material(db_session, file_id=stored.id)

    response = client.get(f"/api/materials/{material.id}/file?token={student_token}")

    assert response.status_code == 200
    assert response.json()["code"] == 401


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
