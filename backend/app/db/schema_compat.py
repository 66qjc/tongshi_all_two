"""数据库结构兼容修复。"""
from sqlalchemy import inspect, text


def ensure_schema_compatibility(engine) -> None:
    """补齐旧数据库缺失的业务字段和关联表。"""
    with engine.begin() as conn:
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())

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

        # ── showcase_items 表（依赖 stored_files）────────────────────────
        if "showcase_items" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE showcase_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        section VARCHAR(32) NOT NULL,
                        title VARCHAR(128) NOT NULL,
                        content TEXT DEFAULT '',
                        cover_file_id INTEGER,
                        link_url VARCHAR(512) DEFAULT '',
                        sort_order INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT 1,
                        created_by VARCHAR(32) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE showcase_items (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        section VARCHAR(32) NOT NULL,
                        title VARCHAR(128) NOT NULL,
                        content TEXT,
                        cover_file_id INTEGER NULL,
                        link_url VARCHAR(512) DEFAULT '',
                        sort_order INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT 1,
                        created_by VARCHAR(32) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        CONSTRAINT fk_showcase_items_cover_file_id
                            FOREIGN KEY (cover_file_id) REFERENCES stored_files(id),
                        CONSTRAINT fk_showcase_items_created_by
                            FOREIGN KEY (created_by) REFERENCES users(id)
                    )
                """))

        # 再次刷新表名集合
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())

        # ── 为业务表补齐 file_id 列 ─────────────────────────────────────
        _add_column_if_missing(
            conn, inspector, "materials", "file_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "courses", "created_by", "VARCHAR(32) NOT NULL DEFAULT 'T001'")
        _add_column_if_missing(
            conn, inspector, "classes", "course_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "materials", "course_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "questions", "course_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "student_progress", "course_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "announcements", "course_id", "INTEGER")
        _add_column_if_missing(conn, inspector, "projects",
                               "report_file_id", "INTEGER")
        _add_column_if_missing(conn, inspector, "projects",
                               "cover_file_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "project_images", "file_id", "INTEGER")

        # ── users 表新增 needs_password_change 列 ────────────────────────
        _add_column_if_missing(
            conn, inspector, "users", "needs_password_change", "BOOLEAN NOT NULL DEFAULT 0")

        # ── 清理旧版遗留列（班级改课程归属 / 章节去除后残留的 NOT NULL 列）──
        # 旧库里这些列为 NOT NULL 且无默认值，新模型已去除/改挂课程，
        # 否则 INSERT 不带这些列会因 NOT NULL 约束失败（如新增班级 500）。
        inspector = inspect(conn)
        # classes.major 已从模型删除：直接删列
        _drop_column_if_exists(conn, inspector, "classes", "major")
        # materials/questions/student_progress 由挂章节改为挂课程：旧 chapter_id 放开为可空
        _make_column_nullable(conn, inspector, "materials", "chapter_id", "INTEGER")
        _make_column_nullable(conn, inspector, "questions", "chapter_id", "INTEGER")
        _make_column_nullable(
            conn, inspector, "student_progress", "chapter_id", "INTEGER")
        # announcements.class_id 改为可空（多班级走 announcement_classes 关联表）
        _make_column_nullable(conn, inspector, "announcements", "class_id", "INTEGER")

        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "announcements" in table_names and "announcement_classes" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE announcement_classes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        announcement_id INTEGER NOT NULL,
                        class_id INTEGER NOT NULL,
                        UNIQUE(announcement_id, class_id),
                        FOREIGN KEY(announcement_id) REFERENCES announcements(id) ON DELETE CASCADE,
                        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE announcement_classes (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        announcement_id INTEGER NOT NULL,
                        class_id INTEGER NOT NULL,
                        UNIQUE KEY uq_announcement_class (announcement_id, class_id),
                        CONSTRAINT fk_announcement_classes_announcement_id
                            FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE,
                        CONSTRAINT fk_announcement_classes_class_id
                            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_announcement_classes_announcement_id ON announcement_classes (announcement_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_announcement_classes_class_id ON announcement_classes (class_id)"
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


def _drop_column_if_exists(conn, inspector, table: str, column: str) -> None:
    """如果表存在且包含指定列，则 ALTER TABLE DROP COLUMN（用于清理已从模型删除的旧列）。"""
    table_names = {t for t in inspector.get_table_names()}
    if table not in table_names:
        return
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))


def _make_column_nullable(conn, inspector, table: str, column: str, col_type: str) -> None:
    """将旧库中残留的 NOT NULL 列放开为可空（仅 MySQL；SQLite 测试库由模型新建无需处理）。"""
    if conn.dialect.name != "mysql":
        return
    table_names = {t for t in inspector.get_table_names()}
    if table not in table_names:
        return
    columns = {c["name"]: c for c in inspector.get_columns(table)}
    col = columns.get(column)
    if col is not None and not col["nullable"]:
        conn.execute(
            text(f"ALTER TABLE {table} MODIFY {column} {col_type} NULL"))
