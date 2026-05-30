"""S3 存储适配器单元测试（moto mock - 不依赖真实 S3 服务）"""
import pytest
import boto3
from moto import mock_aws

from app.services.storage_s3 import S3StorageAdapter
from app.services.storage_service import StoredObject


@pytest.fixture(autouse=True)
def _override_s3_settings(monkeypatch):
    """用 moto 的测试端点覆写 S3 配置。"""
    monkeypatch.setattr("app.services.storage_s3.settings.storage_backend", "s3")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_endpoint", None)
    monkeypatch.setattr("app.services.storage_s3.settings.s3_access_key", "testing")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_secret_key", "testing")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_region", "us-east-1")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_bucket_public", "test-public")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_bucket_private", "test-private")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_force_path_style", True)


@pytest.fixture
def s3_adapter():
    """创建带 moto mock 的 S3StorageAdapter。"""
    with mock_aws():
        # 预创建测试桶
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-public")
        client.create_bucket(Bucket="test-private")

        adapter = S3StorageAdapter()
        yield adapter


class TestS3StorageAdapter:
    """S3 适配器核心操作测试。"""

    def test_save_bytes_and_open_stream(self, s3_adapter):
        """save_bytes 后 open_stream 能正确读取内容。"""
        content = b"Hello S3 from moto"
        stored = s3_adapter.save_bytes(
            content=content,
            object_key="test/hello.txt",
            content_type="text/plain",
        )

        assert stored.storage_provider == "s3"
        assert stored.size_bytes == len(content)
        assert stored.bucket_name == "test-public"

        stream = s3_adapter.open_stream(object_key="test/hello.txt")
        assert stream.read() == content

    def test_save_bytes_to_private_bucket(self, s3_adapter):
        """save_bytes 支持指定私有桶。"""
        stored = s3_adapter.save_bytes(
            content=b"private data",
            object_key="secret/file.bin",
            bucket_name="test-private",
        )
        assert stored.bucket_name == "test-private"

        stream = s3_adapter.open_stream(object_key="secret/file.bin", bucket_name="test-private")
        assert stream.read() == b"private data"

    def test_exists_returns_true_for_existing_file(self, s3_adapter):
        """exists 对已存在文件返回 True。"""
        s3_adapter.save_bytes(content=b"foo", object_key="check/me.txt")
        assert s3_adapter.exists(object_key="check/me.txt") is True

    def test_exists_returns_false_for_missing_file(self, s3_adapter):
        """exists 对不存在的文件返回 False。"""
        assert s3_adapter.exists(object_key="check/nope.txt") is False

    def test_delete_removes_file(self, s3_adapter):
        """delete 后 exists 返回 False。"""
        s3_adapter.save_bytes(content=b"temp", object_key="tmp/delete-me.txt")
        s3_adapter.delete(object_key="tmp/delete-me.txt")
        assert s3_adapter.exists(object_key="tmp/delete-me.txt") is False

    def test_open_stream_raises_filenotfound_for_missing_key(self, s3_adapter):
        """open_stream 对不存在的 Key 抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError, match="S3 对象不存在"):
            s3_adapter.open_stream(object_key="no/such/key.pdf")

    def test_force_path_style_is_enabled(self, monkeypatch):
        """验证 force_path_style=True 时 S3StorageAdapter 可正常构造并使用。"""
        monkeypatch.setattr("app.services.storage_s3.settings.s3_force_path_style", True)
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="test-public")
            adapter = S3StorageAdapter()
            # 适配器正常初始化，可以执行基本操作
            stored = adapter.save_bytes(content=b"path-style test", object_key="ps/test.bin")
            assert stored.storage_provider == "s3"
