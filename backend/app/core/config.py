"""Central configuration loaded from .env"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"

load_dotenv(BACKEND_ENV_FILE, override=True)


def _env(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ""):
            return value
    return default


def _env_int(*keys: str, default: int) -> int:
    raw = _env(*keys, default=str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


class Settings:
    secret_key: str = _env("SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", default=10080)
    allowed_origins: str = _env("ALLOWED_ORIGINS", default="*")
    database_url: str = _env("DATABASE_URL", default="mysql+pymysql://root:123456@127.0.0.1:3306/tongshi?charset=utf8mb4")
    allow_query_token_for_files: bool = _env("ALLOW_QUERY_TOKEN_FOR_FILES", default="false").lower() == "true"
    storage_backend: str = _env("STORAGE_BACKEND", default="local").lower()
    local_upload_dir: str = _env("LOCAL_UPLOAD_DIR", default=str(BACKEND_ROOT / "uploads"))
    s3_endpoint: str = _env("S3_ENDPOINT", default="")
    s3_access_key: str = _env("S3_ACCESS_KEY", default="")
    s3_secret_key: str = _env("S3_SECRET_KEY", default="")
    s3_bucket_public: str = _env("S3_BUCKET_PUBLIC", default="tongshi-public")
    s3_bucket_private: str = _env("S3_BUCKET_PRIVATE", default="tongshi-private")
    s3_region: str = _env("S3_REGION", default="us-east-1")
    s3_force_path_style: bool = _env("S3_FORCE_PATH_STYLE", default="true").lower() == "true"

    def __init__(self):
        if not self.secret_key:
            raise ValueError("SECRET_KEY 未配置，禁止启动")


settings = Settings()
