"""Showcase 图文混排（content_blocks）相关测试"""
import io

import pytest

from tests.conftest import auth_header

TINY_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
    0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xFE,
    0xD7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82,
])


def _admin_token(client) -> str:
    resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def _upload_test_image(client, token: str) -> int:
    resp = client.post(
        "/api/upload",
        files={"file": ("test.png", io.BytesIO(TINY_PNG), "image/png")},
        headers=auth_header(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["file_id"]
    return data["file_id"]


@pytest.fixture(scope="function")
def admin_token(client):
    return _admin_token(client)


@pytest.fixture(scope="function")
def uploaded_file_id(client, admin_token):
    return _upload_test_image(client, admin_token)


class TestShowcaseContentBlocks:
    """测试管理员创建/编辑 content_blocks 图文混排内容。"""

    def test_create_showcase_with_content_blocks(self, client, admin_token, uploaded_file_id):
        blocks = [
            {"type": "text", "data": {"text": "第一段公益课正文。"}},
            {"type": "image", "data": {"file_id": uploaded_file_id, "caption": "活动合影"}},
            {"type": "text", "data": {"text": "第二段总结内容。"}},
        ]
        resp = client.post(
            "/api/showcase",
            json={
                "section": "welfare",
                "title": "测试图文混排公益课",
                "content_blocks": blocks,
                "sort_order": 1,
            },
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["title"] == "测试图文混排公益课"
        assert len(data["content_blocks"]) == 3
        assert data["content_blocks"][1]["data"]["caption"] == "活动合影"
        assert "第一段" in data["content"] and "第二段" in data["content"]
        assert data["content"].endswith("…") or len(data["content"]) <= 121

    def test_create_showcase_rejects_invalid_block_type(self, client, admin_token):
        resp = client.post(
            "/api/showcase",
            json={
                "section": "welfare",
                "title": "测试非法块",
                "content_blocks": [
                    {"type": "video", "data": {"url": "http://example.com"}},
                ],
            },
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 400
        assert resp.json()["message"]

    def test_create_showcase_rejects_missing_image_file_id(self, client, admin_token):
        resp = client.post(
            "/api/showcase",
            json={
                "section": "reading_club",
                "title": "测试无效图片",
                "content_blocks": [
                    {"type": "text", "data": {"text": "正文"}},
                    {"type": "image", "data": {"file_id": 0}},
                ],
            },
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 400

    def test_create_showcase_rejects_nonexistent_image_file(self, client, admin_token):
        resp = client.post(
            "/api/showcase",
            json={
                "section": "reading_club",
                "title": "测试不存在的图片",
                "content_blocks": [
                    {"type": "image", "data": {"file_id": 99999}},
                ],
            },
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 400

    def test_update_showcase_content_blocks(self, client, admin_token, uploaded_file_id):
        # 先创建
        create_resp = client.post(
            "/api/showcase",
            json={
                "section": "welfare",
                "title": "原始内容",
                "content_blocks": [
                    {"type": "text", "data": {"text": "原始文字。"}},
                ],
            },
            headers=auth_header(admin_token),
        )
        item_id = create_resp.json()["data"]["id"]

        # 更新
        update_resp = client.put(
            f"/api/showcase/{item_id}",
            json={
                "content_blocks": [
                    {"type": "text", "data": {"text": "更新后文字。"}},
                    {"type": "image", "data": {"file_id": uploaded_file_id}},
                ],
            },
            headers=auth_header(admin_token),
        )
        assert update_resp.status_code == 200, update_resp.text
        data = update_resp.json()["data"]
        assert len(data["content_blocks"]) == 2
        assert data["content_blocks"][0]["data"]["text"] == "更新后文字。"
        assert data["content_blocks"][1]["data"]["file_id"] == uploaded_file_id

    def test_public_list_returns_content_blocks(self, client, admin_token, uploaded_file_id):
        client.post(
            "/api/showcase",
            json={
                "section": "welfare",
                "title": "公开列表测试",
                "content_blocks": [
                    {"type": "text", "data": {"text": "正文片段。"}},
                    {"type": "image", "data": {"file_id": uploaded_file_id}},
                ],
            },
            headers=auth_header(admin_token),
        )

        resp = client.get("/api/showcase")
        assert resp.status_code == 200
        data = resp.json()["data"]
        welfare_items = data.get("welfare", [])
        target = next((x for x in welfare_items if x["title"] == "公开列表测试"), None)
        assert target is not None
        assert len(target["content_blocks"]) == 2
        assert "正文" in target["content"]

    def test_old_showcase_without_blocks_uses_legacy_rendering(self, client, admin_token):
        # 使用旧字段 content + image_file_ids 创建
        import io
        file_id = _upload_test_image(client, admin_token)
        resp = client.post(
            "/api/showcase",
            json={
                "section": "welfare",
                "title": "旧格式内容",
                "content": "旧正文内容",
                "image_file_ids": [file_id],
            },
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["content"] == "旧正文内容"
        assert data["content_blocks"] == []
        assert len(data["images"]) == 1
