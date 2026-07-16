"""软删除资料后文件签名和文件流访问边界测试。"""

from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.entities import Material, StoredFile
from tests.conftest import auth_header


def test_soft_deleted_material_invalidates_existing_file_access(client, db_session, student_token):
    """资料软删后，旧签名和新签名都不能继续读取文件。"""
    content = b"%PDF-1.4 soft deleted"
    stored = StoredFile(
        biz_type="material",
        storage_provider="local",
        object_key="course/soft-delete.pdf",
        original_name="soft-delete.pdf",
        stored_name="soft-delete.pdf",
        content_type="application/pdf",
        extension=".pdf",
        size_bytes=len(content),
        created_by="T001",
    )
    db_session.add(stored)
    db_session.flush()
    material = Material(
        course_id=1,
        type="pdf",
        title="软删除文件资料",
        url="",
        file_id=stored.id,
    )
    db_session.add(material)
    db_session.commit()

    target = Path(settings.local_upload_dir) / stored.object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    signed = client.post(
        f"/api/files/{stored.id}/access-url",
        headers=auth_header(student_token),
    )
    assert signed.json()["code"] == 0
    old_url = signed.json()["data"]["url"]

    material.deleted_at = datetime.now(timezone.utc)
    material.deleted_by = "T001"
    db_session.commit()

    old_response = client.get(old_url)
    new_response = client.post(
        f"/api/files/{stored.id}/access-url",
        headers=auth_header(student_token),
    )

    assert old_response.status_code == 200
    assert old_response.json()["code"] == 404
    assert new_response.status_code == 200
    assert new_response.json()["code"] == 404
