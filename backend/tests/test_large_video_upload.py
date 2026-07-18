"""单机大视频上传保护回归测试。"""
import io

from app.core.upload_validation import MAX_VIDEO_SIZE
from tests.conftest import auth_header


def _video_content() -> bytes:
    return b"\x00\x00\x00\x18ftypisom" + (b"v" * 1024)


def _upload_video(client, teacher_token, expected_size: int):
    return client.post(
        "/api/upload",
        data={"expected_size": str(expected_size)},
        files={"file": ("large-video.mp4", io.BytesIO(_video_content()), "video/mp4")},
        headers=auth_header(teacher_token),
    )


def test_upload_rejects_declared_video_size_over_limit(client, teacher_token):
    """声明超过 1GiB 的视频必须在读取文件前被拒绝。"""
    response = _upload_video(client, teacher_token, MAX_VIDEO_SIZE + 1)

    assert response.json()["code"] == 400
    assert response.json()["message"] == "视频文件大小超过 1GiB 限制"


def test_upload_rejects_video_when_disk_reserve_is_insufficient(client, teacher_token, monkeypatch):
    """本地磁盘无法保留上传文件和安全余量时必须提前拒绝。"""
    import app.api.v1.routes.upload_routes as upload_routes

    monkeypatch.setattr(
        upload_routes,
        "_get_local_upload_free_bytes",
        lambda: MAX_VIDEO_SIZE + (2 * 1024 * 1024 * 1024) - 1,
        raising=False,
    )

    response = _upload_video(client, teacher_token, MAX_VIDEO_SIZE)

    assert response.json()["code"] == 400
    assert response.json()["message"] == "服务器可用磁盘空间不足，暂时无法接收该视频"


def test_upload_rejects_second_video_while_first_is_in_progress(client, teacher_token, monkeypatch):
    """单 worker 正在接收视频时，第二个视频上传必须明确拒绝。"""
    import app.api.v1.routes.upload_routes as upload_routes

    monkeypatch.setattr(upload_routes, "_video_upload_in_progress", True, raising=False)

    response = _upload_video(client, teacher_token, len(_video_content()))

    assert response.json()["code"] == 429
    assert response.json()["message"] == "已有视频正在上传，请等待完成后再试"


def test_upload_deletes_invalid_video_after_streaming_to_local_storage(client, teacher_token):
    """视频内容校验失败后不得留下已流式写入的临时文件。"""
    import app.services.file_service as file_service

    response = client.post(
        "/api/upload",
        files={"file": ("invalid-video.mp4", io.BytesIO(b"not-a-video"), "video/mp4")},
        headers=auth_header(teacher_token),
    )

    assert response.json()["code"] == 400
    assert not [path for path in file_service._local_adapter.root_dir.rglob("*") if path.is_file()]
