"""数据库结构兼容修复测试"""
import os

from botocore.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings
from app.db.schema_compat import ensure_schema_compatibility
from app.services.storage_s3 import S3StorageAdapter


def test_ensure_schema_compatibility_adds_course_anchor_columns():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY,
                name VARCHAR(128) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name VARCHAR(64) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                type VARCHAR(16) NOT NULL,
                title VARCHAR(128) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY,
                type VARCHAR(16) NOT NULL,
                stem TEXT NOT NULL,
                answer VARCHAR(128) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE student_progress (
                id INTEGER PRIMARY KEY,
                user_id VARCHAR(32) NOT NULL
            )
        """))

    ensure_schema_compatibility(engine)

    inspector = inspect(engine)
    assert "created_by" in {column["name"] for column in inspector.get_columns("courses")}
    assert "course_id" in {column["name"] for column in inspector.get_columns("classes")}
    assert "course_id" in {column["name"] for column in inspector.get_columns("materials")}
    assert "course_id" in {column["name"] for column in inspector.get_columns("questions")}
    assert "course_id" in {column["name"] for column in inspector.get_columns("student_progress")}


def test_ensure_schema_compatibility_creates_project_images_table():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY,
                title VARCHAR(128) NOT NULL
            )
        """))

    ensure_schema_compatibility(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("project_images")}

    assert "project_images" in table_names
    assert {"id", "project_id", "image_url", "sort_order"}.issubset(columns)


def test_settings_defaults_keep_mysql_and_local_storage(monkeypatch):
    """未设置 S3 环境变量时，storage_backend 默认 local，DATABASE_URL 不受影响"""
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://root:123456@127.0.0.1:3306/tongshi?charset=utf8mb4")

    settings = Settings()

    assert settings.database_url.startswith("mysql+pymysql://")
    assert settings.storage_backend in {"local", "s3"}


def test_settings_reads_seaweedfs_s3_config(monkeypatch):
    """应正确读取本地 SeaweedFS S3 配置"""
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:8333")
    monkeypatch.setenv("S3_ACCESS_KEY", "test")
    monkeypatch.setenv("S3_SECRET_KEY", "test")
    monkeypatch.setenv("S3_BUCKET_PUBLIC", "tongshi-public")
    monkeypatch.setenv("S3_BUCKET_PRIVATE", "tongshi-private")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_FORCE_PATH_STYLE", "true")

    settings = Settings()

    assert settings.storage_backend == "s3"
    assert settings.s3_endpoint == "http://localhost:8333"
    assert settings.s3_access_key == "test"
    assert settings.s3_secret_key == "test"
    assert settings.s3_bucket_public == "tongshi-public"
    assert settings.s3_bucket_private == "tongshi-private"
    assert settings.s3_region == "us-east-1"
    assert settings.s3_force_path_style is True


def test_s3_storage_adapter_uses_path_style_for_seaweedfs(monkeypatch):
    """SeaweedFS S3 网关应使用 path-style addressing"""
    monkeypatch.setattr("app.services.storage_s3.settings.s3_endpoint", "http://localhost:8333")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_access_key", "test")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_secret_key", "test")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_region", "us-east-1")
    monkeypatch.setattr("app.services.storage_s3.settings.s3_force_path_style", True)

    captured: dict[str, object] = {}

    class DummyClient:
        pass

    def fake_boto3_client(service_name: str, **kwargs):
        captured["service_name"] = service_name
        captured.update(kwargs)
        return DummyClient()

    monkeypatch.setattr("app.services.storage_s3.boto3.client", fake_boto3_client)

    adapter = S3StorageAdapter()

    assert isinstance(adapter._client, DummyClient)
    assert captured["service_name"] == "s3"
    assert captured["endpoint_url"] == "http://localhost:8333"
    assert captured["aws_access_key_id"] == "test"
    assert captured["aws_secret_access_key"] == "test"
    assert captured["region_name"] == "us-east-1"
    assert isinstance(captured["config"], Config)
    assert captured["config"].s3 == {"addressing_style": "path"}


def test_ensure_schema_compatibility_creates_stored_files_table():
    """兼容脚本应自动创建 stored_files 表"""
    engine = create_engine("sqlite:///:memory:")

    ensure_schema_compatibility(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert "stored_files" in table_names
    columns = {column["name"] for column in inspector.get_columns("stored_files")}
    assert {"id", "biz_type", "biz_id", "storage_provider", "bucket_name",
            "object_key", "original_name", "stored_name", "content_type",
            "extension", "size_bytes", "sha256", "status", "created_by",
            "created_at"}.issubset(columns)


def test_ensure_schema_compatibility_adds_file_columns_to_business_tables():
    """兼容脚本应为 materials、projects、project_images 补齐 file_id 列"""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id VARCHAR(32) PRIMARY KEY,
                name VARCHAR(64) NOT NULL,
                hashed_password VARCHAR(128) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE materials (
                id INTEGER PRIMARY KEY,
                course_id INTEGER NOT NULL,
                type VARCHAR(16) NOT NULL,
                title VARCHAR(128) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY,
                title VARCHAR(128) NOT NULL,
                author_id VARCHAR(32) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE project_images (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                image_url VARCHAR(512) NOT NULL DEFAULT ''
            )
        """))

    ensure_schema_compatibility(engine)

    inspector = inspect(engine)
    mat_cols = {c["name"] for c in inspector.get_columns("materials")}
    proj_cols = {c["name"] for c in inspector.get_columns("projects")}
    img_cols = {c["name"] for c in inspector.get_columns("project_images")}

    assert "file_id" in mat_cols
    assert "report_file_id" in proj_cols
    assert "cover_file_id" in proj_cols
    assert "file_id" in img_cols


def test_ensure_schema_compatibility_drops_legacy_major_column():
    """旧库 classes.major 已从模型删除，兼容脚本应清理该列。"""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name VARCHAR(64) NOT NULL,
                major VARCHAR(64) NOT NULL
            )
        """))

    ensure_schema_compatibility(engine)

    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("classes")}
    assert "major" not in columns


def test_ensure_schema_compatibility_creates_showcase_items_table():
    """兼容脚本应自动创建 showcase_items 表。"""
    engine = create_engine("sqlite:///:memory:")

    ensure_schema_compatibility(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("showcase_items")}

    assert "showcase_items" in table_names
    assert {"id", "section", "title", "content", "cover_file_id", "sort_order", "is_active", "created_by"}.issubset(columns)


def test_ensure_schema_compatibility_creates_announcement_classes_table():
    """兼容脚本应自动创建发布题目与班级的关联表"""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE announcements (
                id INTEGER PRIMARY KEY,
                course_id INTEGER,
                teacher_id VARCHAR(32) NOT NULL,
                type VARCHAR(16) NOT NULL,
                title VARCHAR(128) NOT NULL
            )
        """))

    ensure_schema_compatibility(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("announcement_classes")}

    assert "announcement_classes" in table_names
    assert {"id", "announcement_id", "class_id"}.issubset(columns)
