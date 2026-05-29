"""数据库结构兼容修复。"""
from sqlalchemy import inspect, text


def ensure_schema_compatibility(engine) -> None:
    """补齐旧数据库缺失的业务字段和关联表。"""
    with engine.begin() as conn:
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())

        if "chapters" in table_names:
            columns = {column["name"]
                       for column in inspector.get_columns("chapters")}
            required_columns = [
                ("day_of_week", "VARCHAR(16)", "''"),
                ("class_periods", "VARCHAR(32)", "''"),
                ("schedule_note", "VARCHAR(128)", "''"),
            ]

            for name, column_type, default_value in required_columns:
                if name not in columns:
                    conn.execute(text(
                        f"ALTER TABLE chapters ADD COLUMN {name} {column_type} DEFAULT {default_value}"
                    ))

        if "projects" in table_names and "project_images" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE project_images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER NOT NULL,
                        image_url VARCHAR(512) NOT NULL DEFAULT '',
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE project_images (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        project_id INTEGER NOT NULL,
                        image_url VARCHAR(512) NOT NULL DEFAULT '',
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        CONSTRAINT fk_project_images_project_id
                            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                    )
                """))

            conn.execute(text(
                "CREATE INDEX ix_project_images_project_id ON project_images (project_id)"
            ))

        # ── stored_files 表 ───────────────────────────────────────────────
        if "stored_files" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE stored_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        biz_type VARCHAR(32) NOT NULL DEFAULT '',
                        biz_id INTEGER,
                        storage_provider VARCHAR(16) NOT NULL DEFAULT 'local',
                        bucket_name VARCHAR(128) DEFAULT '',
                        object_key VARCHAR(512) NOT NULL DEFAULT '',
                        original_name VARCHAR(255) NOT NULL DEFAULT '',
                        stored_name VARCHAR(255) NOT NULL DEFAULT '',
                        content_type VARCHAR(128) DEFAULT '',
                        extension VARCHAR(32) DEFAULT '',
                        size_bytes INTEGER NOT NULL DEFAULT 0,
                        sha256 VARCHAR(64) DEFAULT '',
                        status VARCHAR(16) NOT NULL DEFAULT 'active',
                        created_by VARCHAR(32) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE stored_files (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        biz_type VARCHAR(32) NOT NULL DEFAULT '',
                        biz_id INTEGER NULL,
                        storage_provider VARCHAR(16) NOT NULL DEFAULT 'local',
                        bucket_name VARCHAR(128) DEFAULT '',
                        object_key VARCHAR(512) NOT NULL DEFAULT '',
                        original_name VARCHAR(255) NOT NULL DEFAULT '',
                        stored_name VARCHAR(255) NOT NULL DEFAULT '',
                        content_type VARCHAR(128) DEFAULT '',
                        extension VARCHAR(32) DEFAULT '',
                        size_bytes INTEGER NOT NULL DEFAULT 0,
                        sha256 VARCHAR(64) DEFAULT '',
                        status VARCHAR(16) NOT NULL DEFAULT 'active',
                        created_by VARCHAR(32) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

            conn.execute(text(
                "CREATE INDEX ix_stored_files_biz_id ON stored_files (biz_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_stored_files_created_by ON stored_files (created_by)"
            ))

        # 刷新表名集合（stored_files 可能刚创建）
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())

        # ── 为业务表补齐 file_id 列 ─────────────────────────────────────
        _add_column_if_missing(
            conn, inspector, "materials", "file_id", "INTEGER")
        _add_column_if_missing(conn, inspector, "projects",
                               "report_file_id", "INTEGER")
        _add_column_if_missing(conn, inspector, "projects",
                               "cover_file_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "project_images", "file_id", "INTEGER")

        # ── users 表新增 needs_password_change 列 ────────────────────────
        _add_column_if_missing(
            conn, inspector, "users", "needs_password_change", "BOOLEAN NOT NULL DEFAULT 0")

        # ── user_notifications 表 ───────────────────────────────────────
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "user_notifications" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE user_notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(32) NOT NULL,
                        type VARCHAR(32) NOT NULL DEFAULT '',
                        title VARCHAR(128) NOT NULL DEFAULT '',
                        content TEXT DEFAULT '',
                        related_type VARCHAR(32) DEFAULT '',
                        related_id INTEGER,
                        is_read BOOLEAN NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE user_notifications (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(32) NOT NULL,
                        type VARCHAR(32) NOT NULL DEFAULT '',
                        title VARCHAR(128) NOT NULL DEFAULT '',
                        content TEXT,
                        related_type VARCHAR(32) DEFAULT '',
                        related_id INTEGER NULL,
                        is_read BOOLEAN NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_user_notifications_user_id
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))

            conn.execute(text(
                "CREATE INDEX ix_user_notifications_user_id ON user_notifications (user_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_user_notifications_related_id ON user_notifications (related_id)"
            ))


def _add_column_if_missing(conn, inspector, table: str, column: str, col_type: str) -> None:
    """如果表存在且缺少指定列，则 ALTER TABLE ADD COLUMN。"""
    table_names = {t for t in inspector.get_table_names()}
    if table not in table_names:
        return
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column not in existing:
        conn.execute(
            text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
