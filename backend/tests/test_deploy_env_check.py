from pathlib import Path

from scripts.check_deploy_env import check_deploy_env


def _write_env(path: Path, content: str) -> Path:
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def test_local_storage_env_passes_when_upload_dir_is_writable(tmp_path):
    """本地存储部署配置应只要求上传目录可写，不要求 S3 端点存在。"""
    upload_dir = tmp_path / "uploads"
    env_file = _write_env(
        tmp_path / ".env",
        f"""
SECRET_KEY=abcdefghijklmnopqrstuvwxyz123456
ALLOWED_ORIGINS=https://tongshi.example.com
DATABASE_URL=mysql+pymysql://tongshi_user:strong-password@127.0.0.1:3306/tongshi?charset=utf8mb4
STORAGE_BACKEND=local
LOCAL_UPLOAD_DIR={upload_dir}
""",
    )

    result = check_deploy_env(env_file, check_mysql=False, check_s3=False)

    assert result.ok is True
    assert result.storage_backend == "local"
    assert any("本地上传目录可写" in message for message in result.messages)
    assert not any("S3" in message for message in result.messages)


def test_local_storage_env_fails_for_unsafe_defaults(tmp_path):
    """上线检查应拒绝默认密钥、默认数据库口令和通配 CORS。"""
    env_file = _write_env(
        tmp_path / ".env",
        """
SECRET_KEY=tongshi-demo-secret
ALLOWED_ORIGINS=*
DATABASE_URL=mysql+pymysql://root:123456@127.0.0.1:3306/tongshi?charset=utf8mb4
STORAGE_BACKEND=local
""",
    )

    result = check_deploy_env(env_file, check_mysql=False, check_s3=False)

    assert result.ok is False
    assert "SECRET_KEY 长度必须至少 32 位" in result.errors
    assert "生产环境 ALLOWED_ORIGINS 不能为 *" in result.errors
    assert "DATABASE_URL 不能使用 root:123456 默认账号口令" in result.errors


def test_s3_storage_env_requires_endpoint_when_enabled(tmp_path):
    """只有显式启用 S3 时才要求配置 S3_ENDPOINT。"""
    env_file = _write_env(
        tmp_path / ".env",
        """
SECRET_KEY=abcdefghijklmnopqrstuvwxyz123456
ALLOWED_ORIGINS=https://tongshi.example.com
DATABASE_URL=mysql+pymysql://tongshi_user:strong-password@127.0.0.1:3306/tongshi?charset=utf8mb4
STORAGE_BACKEND=s3
""",
    )

    result = check_deploy_env(env_file, check_mysql=False, check_s3=False)

    assert result.ok is False
    assert "STORAGE_BACKEND=s3 时必须配置 S3_ENDPOINT" in result.errors
