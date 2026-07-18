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
    def __init__(self):
        self.secret_key: str = _env("SECRET_KEY")
        self.algorithm: str = "HS256"
        self.access_token_expire_minutes: int = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", default=10080)
        self.allowed_origins: str = _env("ALLOWED_ORIGINS", default="*")
        self.database_url: str = _env(
            "DATABASE_URL",
            default="mysql+pymysql://root:123456@127.0.0.1:3306/tongshi?charset=utf8mb4",
        )
        self.db_pool_size = _env_int("DB_POOL_SIZE", default=5)
        self.db_max_overflow = _env_int("DB_MAX_OVERFLOW", default=5)
        self.db_pool_recycle = _env_int("DB_POOL_RECYCLE", default=3600)
        self.db_pool_timeout = _env_int("DB_POOL_TIMEOUT", default=30)
        self.storage_backend: str = _env("STORAGE_BACKEND", default="local").lower()
        self.local_upload_dir: str = _env("LOCAL_UPLOAD_DIR", default=str(BACKEND_ROOT / "uploads"))
        self.s3_endpoint: str = _env("S3_ENDPOINT", default="")
        self.s3_access_key: str = _env("S3_ACCESS_KEY", default="")
        self.s3_secret_key: str = _env("S3_SECRET_KEY", default="")
        self.s3_bucket_public: str = _env("S3_BUCKET_PUBLIC", default="tongshi-public")
        self.s3_bucket_private: str = _env("S3_BUCKET_PRIVATE", default="tongshi-private")
        self.s3_region: str = _env("S3_REGION", default="us-east-1")
        self.s3_force_path_style: bool = _env("S3_FORCE_PATH_STYLE", default="true").lower() == "true"
        # Redis 配置
        self.redis_host: str = _env("REDIS_HOST", default="127.0.0.1")
        self.redis_port: int = _env_int("REDIS_PORT", default=6379)
        self.redis_password: str = _env("REDIS_PASSWORD", default="")
        self.redis_db: int = _env_int("REDIS_DB", default=0)
        self.redis_pool_size: int = _env_int("REDIS_POOL_SIZE", default=10)
        self.redis_socket_timeout: int = _env_int("REDIS_SOCKET_TIMEOUT", default=5)
        if not self.secret_key:
            raise ValueError("SECRET_KEY 未配置，禁止启动")


settings = Settings()
