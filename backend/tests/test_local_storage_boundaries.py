import shutil
from pathlib import Path

import pytest

from app.models.entities import Material, StoredFile
from app.services import file_service
from app.services.storage_local import LocalStorageAdapter
from tests.conftest import auth_header


def test_local_storage_rejects_path_traversal():
    root = Path(__file__).resolve().parents[1] / ".test-local-storage-boundaries"
    shutil.rmtree(root, ignore_errors=True)
    adapter = LocalStorageAdapter(root)

    try:
        with pytest.raises(ValueError):
            adapter.exists(object_key="../secret.txt")

        with pytest.raises(ValueError):
            adapter.open_stream(object_key="../secret.txt")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_access_url_authorization_does_not_touch_storage(
    client,
    db_session,
    teacher_token,
    monkeypatch,
):
    stored = StoredFile(
        biz_type="material",
        storage_provider="local",
        bucket_name="",
        object_key="missing-but-authorized.pdf",
        original_name="missing.pdf",
        stored_name="missing.pdf",
        content_type="application/pdf",
        extension=".pdf",
        size_bytes=123,
        created_by="T001",
    )
    db_session.add(stored)
    db_session.flush()
    db_session.add(Material(
        course_id=1,
        type="pdf",
        title="仅鉴权资料",
        file_id=stored.id,
    ))
    db_session.commit()

    def fail_storage_call(*args, **kwargs):
        pytest.fail("申请文件访问 URL 时不应访问存储适配器")

    monkeypatch.setattr(file_service._local_adapter, "exists", fail_storage_call)
    monkeypatch.setattr(file_service._local_adapter, "open_stream", fail_storage_call)

    response = client.post(
        f"/api/files/{stored.id}/access-url",
        headers=auth_header(teacher_token),
    ).json()

    assert response["code"] == 0
    assert response["data"]["expires_in"] == 300
