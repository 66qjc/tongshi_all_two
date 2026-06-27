"""管理员端公共课程资料上传校验回归测试。"""

import pytest
from fastapi.testclient import TestClient

from app.models.entities import Course, Material, StoredFile


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def build_stored_file(db_session, filename: str, content_type: str, extension: str, owner: str = "admin") -> int:
    """在测试中直接构造一条 stored_files 记录，无需真正上传。"""
    sf = StoredFile(
        biz_type="public_course_material",
        storage_provider="local",
        object_key=f"test/{filename}",
        original_name=filename,
        stored_name=filename,
        extension=extension,
        content_type=content_type,
        size_bytes=100,
        sha256="0" * 64,
        status="active",
        created_by=owner,
    )
    db_session.add(sf)
    db_session.commit()
    db_session.refresh(sf)
    return sf.id


class TestAdminPublicMaterialUploadValidation:
    @pytest.fixture
    def admin_token(self, client: TestClient):
        resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
        return resp.json()["data"]["access_token"]

    @pytest.fixture
    def public_course_id(self, client: TestClient, admin_token: str):
        resp = client.post(
            "/api/admin/public-courses",
            json={"name": "资料校验公共课"},
            headers=auth_header(admin_token),
        )
        assert resp.json()["code"] == 0
        return resp.json()["data"]["id"]

    def test_create_material_without_file_id_rejected(
        self, client: TestClient, admin_token: str, public_course_id: int
    ):
        """视频/PDF 资料必须关联 file_id。"""
        resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "video", "title": "无文件视频", "url": "/x.mp4", "size": "1 MB"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 400, f"预期返回 400，实际 {data}"

    def test_create_material_invalid_file_id_rejected(
        self, client: TestClient, admin_token: str, public_course_id: int
    ):
        """file_id 不存在时被拒绝。"""
        resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "pdf", "title": "假文件资料", "url": "/x.pdf", "size": "1 MB", "file_id": 999999},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 400, f"预期返回 400，实际 {data}"

    def test_create_pdf_material_rejects_video_file(
        self, client: TestClient, admin_token: str, public_course_id: int, db_session
    ):
        """资料类型为 PDF 但关联视频文件时被拒绝。"""
        file_id = build_stored_file(db_session, "clip.mp4", "video/mp4", ".mp4")
        resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "pdf", "title": "PDF 资料", "url": "/x.pdf", "size": "1 MB", "file_id": file_id},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 400, f"预期返回 400，实际 {data}"

    def test_create_video_material_rejects_pdf_file(
        self, client: TestClient, admin_token: str, public_course_id: int, db_session
    ):
        """资料类型为视频但关联 PDF 文件时被拒绝。"""
        file_id = build_stored_file(db_session, "note.pdf", "application/pdf", ".pdf")
        resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "video", "title": "视频资料", "url": "/x.mp4", "size": "1 MB", "file_id": file_id},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 400, f"预期返回 400，实际 {data}"

    def test_create_pdf_material_accepts_pdf_file(
        self, client: TestClient, admin_token: str, public_course_id: int, db_session, teacher_token
    ):
        """类型与文件一致时创建成功并同步到教师副本。"""
        client.post(
            f"/api/questions/courses/{public_course_id}/add",
            headers=auth_header(teacher_token),
        )
        file_id = build_stored_file(db_session, "note.pdf", "application/pdf", ".pdf")
        resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "pdf", "title": "有效 PDF 资料", "url": "/x.pdf", "size": "1 MB", "file_id": file_id},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0, f"预期创建成功，实际 {data}"

        source_id = data["data"]["id"]
        copies = db_session.query(Course).filter(Course.source_course_id == public_course_id).all()
        assert len(copies) == 1
        mirrored = db_session.query(Material).filter(
            Material.course_id == copies[0].id,
            Material.source_material_id == source_id,
        ).first()
        assert mirrored is not None
        assert mirrored.title == "有效 PDF 资料"

    def test_update_material_rejects_type_mismatch(
        self, client: TestClient, admin_token: str, public_course_id: int, db_session
    ):
        """修改资料时类型与新文件类型不匹配被拒绝。"""
        pdf_file_id = build_stored_file(db_session, "note.pdf", "application/pdf", ".pdf")
        create_resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "pdf", "title": "原资料", "url": "/x.pdf", "size": "1 MB", "file_id": pdf_file_id},
            headers=auth_header(admin_token),
        )
        material_id = create_resp.json()["data"]["id"]

        update_resp = client.put(
            f"/api/admin/public-courses/{public_course_id}/materials/{material_id}",
            json={"type": "video", "title": "改为视频", "url": "/x.mp4", "size": "1 MB", "file_id": pdf_file_id},
            headers=auth_header(admin_token),
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["code"] == 400, f"预期返回 400，实际 {data}"

    def test_create_material_rejects_long_title(
        self, client: TestClient, admin_token: str, public_course_id: int, db_session
    ):
        """标题超过 128 字符被拒绝。"""
        file_id = build_stored_file(db_session, "note.pdf", "application/pdf", ".pdf")
        resp = client.post(
            f"/api/admin/public-courses/{public_course_id}/materials",
            json={"type": "pdf", "title": "A" * 129, "url": "/x.pdf", "size": "1 MB", "file_id": file_id},
            headers=auth_header(admin_token),
        )
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert resp.json()["code"] != 0
        else:
            assert "detail" in resp.json()
