"""数据库结构兼容修复。"""
from sqlalchemy import inspect, text


def ensure_schema_compatibility(engine) -> None:
    """补齐旧数据库缺失的业务字段和关联表。"""
    with engine.begin() as conn:
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())

        # question_contribution_logs 表
        if "question_contribution_logs" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE question_contribution_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        public_course_id INTEGER NOT NULL,
                        public_course_name VARCHAR(128) NOT NULL DEFAULT '',
                        operator_id VARCHAR(32) NOT NULL,
                        operator_name VARCHAR(64) NOT NULL DEFAULT '',
                        operator_role VARCHAR(16) NOT NULL DEFAULT '',
                        action VARCHAR(16) NOT NULL,
                        question_count INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE question_contribution_logs (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        public_course_id INTEGER NOT NULL,
                        public_course_name VARCHAR(128) NOT NULL DEFAULT '',
                        operator_id VARCHAR(32) NOT NULL,
                        operator_name VARCHAR(64) NOT NULL DEFAULT '',
                        operator_role VARCHAR(16) NOT NULL DEFAULT '',
                        action VARCHAR(16) NOT NULL,
                        question_count INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_question_contribution_logs_public_course_id ON question_contribution_logs (public_course_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_question_contribution_logs_operator_id ON question_contribution_logs (operator_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_question_contribution_logs_created_at ON question_contribution_logs (created_at)"
            ))


        # lesson_progress 表：课时级学习进度
        if "lesson_progress" not in table_names and {"users", "courses", "lessons"}.issubset(table_names):
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE lesson_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(32) NOT NULL,
                        course_id INTEGER NOT NULL,
                        lesson_id INTEGER NOT NULL,
                        status VARCHAR(16) NOT NULL DEFAULT 'not_started',
                        progress_percent INTEGER NOT NULL DEFAULT 0,
                        last_position INTEGER NOT NULL DEFAULT 0,
                        duration_seconds INTEGER NOT NULL DEFAULT 0,
                        first_viewed_at TIMESTAMP,
                        last_viewed_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        view_count INTEGER NOT NULL DEFAULT 0,
                        CONSTRAINT uq_lesson_progress_user_lesson UNIQUE (user_id, lesson_id),
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
                        FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE lesson_progress (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(32) NOT NULL,
                        course_id INTEGER NOT NULL,
                        lesson_id INTEGER NOT NULL,
                        status VARCHAR(16) NOT NULL DEFAULT 'not_started',
                        progress_percent INTEGER NOT NULL DEFAULT 0,
                        last_position INTEGER NOT NULL DEFAULT 0,
                        duration_seconds INTEGER NOT NULL DEFAULT 0,
                        first_viewed_at DATETIME NULL,
                        last_viewed_at DATETIME NULL,
                        completed_at DATETIME NULL,
                        view_count INTEGER NOT NULL DEFAULT 0,
                        CONSTRAINT uq_lesson_progress_user_lesson UNIQUE (user_id, lesson_id),
                        CONSTRAINT fk_lesson_progress_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        CONSTRAINT fk_lesson_progress_course_id FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                        CONSTRAINT fk_lesson_progress_lesson_id FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_lesson_progress_user_course ON lesson_progress (user_id, course_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_lesson_progress_status ON lesson_progress (status)"
            ))

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

        # ── showcase_item_images 表（依赖 showcase_items）─────────────────
        if "showcase_item_images" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE showcase_item_images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        showcase_item_id INTEGER NOT NULL,
                        file_id INTEGER NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(showcase_item_id) REFERENCES showcase_items(id) ON DELETE CASCADE,
                        FOREIGN KEY(file_id) REFERENCES stored_files(id)
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE showcase_item_images (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        showcase_item_id INTEGER NOT NULL,
                        file_id INTEGER NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_showcase_item_images_showcase_item_id
                            FOREIGN KEY (showcase_item_id) REFERENCES showcase_items(id) ON DELETE CASCADE,
                        CONSTRAINT fk_showcase_item_images_file_id
                            FOREIGN KEY (file_id) REFERENCES stored_files(id)
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_showcase_item_images_showcase_item_id ON showcase_item_images (showcase_item_id)"
            ))

        # ── 为业务表补齐 file_id 列 ─────────────────────────────────────
        _add_column_if_missing(
            conn, inspector, "materials", "file_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "courses", "created_by", "VARCHAR(32) NOT NULL DEFAULT 'T001'")
        _add_column_if_missing(
            conn, inspector, "courses", "is_public", "BOOLEAN NOT NULL DEFAULT 0")
        _add_column_if_missing(
            conn, inspector, "courses", "source_course_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "courses", "question_bank_root_course_id", "INTEGER")
        _ensure_course_name_owner_unique(conn, inspector)
        _add_column_if_missing(
            conn, inspector, "classes", "course_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "classes", "created_by", "VARCHAR(32)")
        _add_column_if_missing(
            conn, inspector, "materials", "course_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "materials", "source_material_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "questions", "course_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "questions", "source_question_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "questions", "tags", "JSON")
        _add_column_if_missing(
            conn, inspector, "quiz_attempts", "announcement_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "announcements", "course_id", "INTEGER")
        _add_column_if_missing(conn, inspector, "projects",
                               "course_id", "INTEGER")
        _add_column_if_missing(conn, inspector, "projects",
                               "report_file_id", "INTEGER")
        _add_column_if_missing(conn, inspector, "projects",
                               "cover_file_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "project_images", "file_id", "INTEGER")
        _add_column_if_missing(
            conn, inspector, "student_class_enrollment", "import_order", "INTEGER NOT NULL DEFAULT 0")

        # ── questions 表新增题库优化字段 ────────────────────────────
        _add_column_if_missing(
            conn, inspector, "questions", "created_by", "VARCHAR(32) NULL")
        _add_column_if_missing(
            conn, inspector, "questions", "star_rating", "INTEGER NOT NULL DEFAULT 3")
        _add_column_if_missing(
            conn, inspector, "questions", "stem_hash", "VARCHAR(64) NULL")

        # ── users 表新增 needs_password_change / token_version 列 ──────────
        _add_column_if_missing(
            conn, inspector, "users", "needs_password_change", "BOOLEAN NOT NULL DEFAULT 0")
        # token_version：改密时递增，使所有旧 JWT 立即失效
        _add_column_if_missing(
            conn, inspector, "users", "token_version", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(
            conn, inspector, "password_reset_requests", "temp_password", "VARCHAR(32) NULL")

        # ── showcase_items 表新增 content_blocks 列（图文混排）──────────
        _showcase_cb_type = "JSON" if conn.dialect.name == "mysql" else "TEXT"
        _add_column_if_missing(
            conn, inspector, "showcase_items", "content_blocks", _showcase_cb_type)


        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "student_class_enrollment" in table_names:
            enrollment_columns = {c["name"] for c in inspector.get_columns("student_class_enrollment")}
            if "import_order" in enrollment_columns:
                conn.execute(text("""
                    UPDATE student_class_enrollment
                    SET import_order = id
                    WHERE import_order IS NULL OR import_order = 0
                """))

        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "classes" in table_names and "courses" in table_names:
            class_columns = {c["name"] for c in inspector.get_columns("classes")}
            if {"created_by", "course_id"}.issubset(class_columns):
                if conn.dialect.name == "mysql":
                    conn.execute(text("""
                        UPDATE classes c
                        JOIN courses co ON co.id = c.course_id
                        SET c.created_by = co.created_by
                        WHERE c.created_by IS NULL OR c.created_by = ''
                    """))
                    conn.execute(text(
                        "UPDATE classes SET created_by = 'T001' WHERE created_by IS NULL OR created_by = ''"))
                    conn.execute(text(
                        "ALTER TABLE classes MODIFY created_by VARCHAR(32) NOT NULL"))
                else:
                    conn.execute(text("""
                        UPDATE classes
                        SET created_by = (
                            SELECT courses.created_by
                            FROM courses
                            WHERE courses.id = classes.course_id
                        )
                        WHERE created_by IS NULL OR created_by = ''
                        """))

        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "courses" in table_names:
            course_columns = {c["name"] for c in inspector.get_columns("courses")}
            if "question_bank_root_course_id" in course_columns:
                if conn.dialect.name == "mysql":
                    conn.execute(text("""
                        UPDATE courses
                        SET question_bank_root_course_id = NULL
                        WHERE question_bank_root_course_id IS NULL
                    """))
                    root_course = conn.execute(text("""
                        SELECT id
                        FROM courses
                        ORDER BY is_public DESC, id ASC
                        LIMIT 1
                    """)).fetchone()
                    if root_course is not None:
                        root_id = root_course[0]
                        conn.execute(text(f"""
                            UPDATE courses
                            SET question_bank_root_course_id = CASE
                                WHEN id = {root_id} THEN NULL
                                ELSE {root_id}
                            END
                        """))
                else:
                    root_course = conn.execute(text("""
                        SELECT id
                        FROM courses
                        ORDER BY is_public DESC, id ASC
                        LIMIT 1
                    """)).fetchone()
                    if root_course is not None:
                        root_id = root_course[0]
                        conn.execute(text("""
                            UPDATE courses
                            SET question_bank_root_course_id = CASE
                                WHEN id = :root_id THEN NULL
                                ELSE :root_id
                            END
                        """), {"root_id": root_id})
                    conn.execute(text(
                        "UPDATE classes SET created_by = 'T001' WHERE created_by IS NULL OR created_by = ''"))

        # ── 清理旧版遗留列（班级改课程归属 / 章节去除后残留的 NOT NULL 列）──
        # 旧库里这些列为 NOT NULL 且无默认值，新模型已去除/改挂课程，
        # 否则 INSERT 不带这些列会因 NOT NULL 约束失败（如新增班级 500）。
        inspector = inspect(conn)
        # classes.major 已从模型删除：直接删列
        _drop_column_if_exists(conn, inspector, "classes", "major")
        # materials/questions 由挂章节改为挂课程：旧 chapter_id 放开为可空
        _make_column_nullable(conn, inspector, "materials", "chapter_id", "INTEGER")
        _make_column_nullable(conn, inspector, "questions", "chapter_id", "INTEGER")
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

        # ── security_questions 表 ─────────────────────────────────────
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "security_questions" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE security_questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(32) NOT NULL,
                        question VARCHAR(200) NOT NULL,
                        answer_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE security_questions (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(32) NOT NULL,
                        question VARCHAR(200) NOT NULL,
                        answer_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_security_questions_user_id
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_security_questions_user_id ON security_questions (user_id)"
            ))

        # ── password_reset_requests 表 ───────────────────────────────────
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "password_reset_requests" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE password_reset_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(32) NOT NULL,
                        message TEXT NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        resolved_by VARCHAR(32),
                        new_password_hash VARCHAR(255),
                        resolved_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY(resolved_by) REFERENCES users(id)
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE password_reset_requests (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(32) NOT NULL,
                        message TEXT NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        resolved_by VARCHAR(32) NULL,
                        new_password_hash VARCHAR(255) NULL,
                        resolved_at TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_password_reset_requests_user_id
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        CONSTRAINT fk_password_reset_requests_resolved_by
                            FOREIGN KEY (resolved_by) REFERENCES users(id)
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_password_reset_requests_user_id ON password_reset_requests (user_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_password_reset_requests_resolved_by ON password_reset_requests (resolved_by)"
            ))

        # course_stages
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "course_stages" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE course_stages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        course_id INTEGER NOT NULL,
                        source_stage_id INTEGER,
                        name VARCHAR(64) NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE course_stages (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        course_id INTEGER NOT NULL,
                        source_stage_id INTEGER NULL,
                        name VARCHAR(64) NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_course_stages_course_id
                            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_course_stages_course_id ON course_stages (course_id)"
            ))

        # materials.stage_id
        if "materials" in table_names:
            _add_column_if_missing(conn, inspector, "materials", "stage_id", "INTEGER NULL")
            indexes = inspector.get_indexes("materials")
            if not any(index.get("name") == "ix_materials_stage_id" for index in indexes):
                conn.execute(text("CREATE INDEX ix_materials_stage_id ON materials (stage_id)"))

        # course_stages.source_stage_id 索引和外键约束补齐
        if "course_stages" in table_names:
            inspector = inspect(conn)
            stage_indexes = {idx["name"] for idx in inspector.get_indexes("course_stages")}
            if "ix_course_stages_source_stage_id" not in stage_indexes:
                conn.execute(text(
                    "CREATE INDEX ix_course_stages_source_stage_id ON course_stages (source_stage_id)"
                ))
            # MySQL 旧库迁移可能缺少 source_stage_id 的 FK 约束
            if conn.dialect.name == "mysql":
                fks = {fk["name"] for fk in inspector.get_foreign_keys("course_stages")}
                if "fk_course_stages_source_stage_id" not in fks:
                    conn.execute(text("""
                        ALTER TABLE course_stages
                        ADD CONSTRAINT fk_course_stages_source_stage_id
                            FOREIGN KEY (source_stage_id) REFERENCES course_stages(id) ON DELETE SET NULL
                    """))

        # ── material_previews 表（依赖 materials 和 stored_files）──────────
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "materials" in table_names and "material_previews" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE material_previews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        material_id INTEGER NOT NULL UNIQUE,
                        status VARCHAR(16) NOT NULL DEFAULT 'pending',
                        cover_file_id INTEGER,
                        summary TEXT DEFAULT '',
                        page_count INTEGER NOT NULL DEFAULT 0,
                        duration_seconds INTEGER NOT NULL DEFAULT 0,
                        resolution VARCHAR(32) DEFAULT '',
                        error_message VARCHAR(256) DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE CASCADE,
                        FOREIGN KEY(cover_file_id) REFERENCES stored_files(id)
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE material_previews (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        material_id INTEGER NOT NULL UNIQUE,
                        status VARCHAR(16) NOT NULL DEFAULT 'pending',
                        cover_file_id INTEGER NULL,
                        summary TEXT,
                        page_count INTEGER NOT NULL DEFAULT 0,
                        duration_seconds INTEGER NOT NULL DEFAULT 0,
                        resolution VARCHAR(32) DEFAULT '',
                        error_message VARCHAR(256) DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        CONSTRAINT fk_material_previews_material_id
                            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
                        CONSTRAINT fk_material_previews_cover_file_id
                            FOREIGN KEY (cover_file_id) REFERENCES stored_files(id)
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_material_previews_material_id ON material_previews (material_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_material_previews_cover_file_id ON material_previews (cover_file_id)"
            ))

        # ── lessons 表（学习页面图文一体）──────────────────────────────────
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "lessons" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE lessons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        course_id INTEGER NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        content TEXT NOT NULL DEFAULT '',
                        status VARCHAR(16) NOT NULL DEFAULT 'published',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE lessons (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        course_id INTEGER NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        content TEXT NOT NULL,
                        status ENUM('draft', 'published') NOT NULL DEFAULT 'published',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        CONSTRAINT fk_lessons_course_id
                            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
                    )
                """))
            conn.execute(text("CREATE INDEX ix_lessons_course_id ON lessons (course_id)"))
            conn.execute(text("CREATE INDEX ix_lessons_sort_order ON lessons (sort_order)"))

        # ── course_progress 表（学习进度）────────────────────────────────────
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "course_progress" not in table_names:
            dialect_name = conn.dialect.name
            if dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE course_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(32) NOT NULL,
                        course_id INTEGER NOT NULL,
                        last_lesson_id INTEGER,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
                        FOREIGN KEY(last_lesson_id) REFERENCES lessons(id) ON DELETE SET NULL,
                        UNIQUE(user_id, course_id)
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE course_progress (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(32) NOT NULL,
                        course_id INTEGER NOT NULL,
                        last_lesson_id INTEGER NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        CONSTRAINT fk_course_progress_user_id
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        CONSTRAINT fk_course_progress_course_id
                            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                        CONSTRAINT fk_course_progress_last_lesson_id
                            FOREIGN KEY (last_lesson_id) REFERENCES lessons(id) ON DELETE SET NULL,
                        UNIQUE KEY uq_course_progress_user_course (user_id, course_id)
                    )
                """))
            conn.execute(text("CREATE INDEX ix_course_progress_user_id ON course_progress (user_id)"))
            conn.execute(text("CREATE INDEX ix_course_progress_course_id ON course_progress (course_id)"))

        # courses.description
        if "courses" in table_names:
            _add_column_if_missing(conn, inspector, "courses", "description", "TEXT NULL")

        # ── CHECK 约束：资料类型和题目类型枚举（仅 MySQL 8.0.16+）─────────
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "materials" in table_names:
            _ensure_check_constraint(
                conn, inspector, "materials", "ck_materials_type",
                "type IN ('video', 'pdf', 'link')"
            )
        if "questions" in table_names:
            _ensure_check_constraint(
                conn, inspector, "questions", "ck_questions_type",
                "type IN ('choice', 'fill', 'multi_choice')"
            )


        # ── 软删除字段、通知扩展和审计日志表 ─────────────────────────────
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        for table in ["users", "courses", "classes", "announcements", "projects", "materials", "questions"]:
            _add_column_if_missing(conn, inspector, table, "deleted_at", "DATETIME NULL")
            _add_column_if_missing(conn, inspector, table, "deleted_by", "VARCHAR(32) NULL")

        inspector = inspect(conn)
        if "student_notifications" in table_names:
            _add_column_if_missing(conn, inspector, "student_notifications", "category", "VARCHAR(32) NOT NULL DEFAULT 'project'")
            _add_column_if_missing(conn, inspector, "student_notifications", "priority", "VARCHAR(16) NOT NULL DEFAULT 'normal'")
            _add_column_if_missing(conn, inspector, "student_notifications", "action_url", "VARCHAR(512) DEFAULT ''")
            _add_column_if_missing(conn, inspector, "student_notifications", "extra_data", "JSON NULL" if conn.dialect.name != "sqlite" else "TEXT")
            _add_column_if_missing(conn, inspector, "student_notifications", "expires_at", "DATETIME NULL")
            _add_column_if_missing(conn, inspector, "student_notifications", "sent_at", "DATETIME NULL")

        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "notification_preferences" not in table_names:
            if conn.dialect.name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE notification_preferences (
                        user_id VARCHAR(32) PRIMARY KEY,
                        enable_assignment_due BOOLEAN NOT NULL DEFAULT 1,
                        enable_grade_published BOOLEAN NOT NULL DEFAULT 1,
                        enable_course_update BOOLEAN NOT NULL DEFAULT 1,
                        enable_project_review BOOLEAN NOT NULL DEFAULT 1,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE notification_preferences (
                        user_id VARCHAR(32) NOT NULL PRIMARY KEY,
                        enable_assignment_due BOOLEAN NOT NULL DEFAULT TRUE,
                        enable_grade_published BOOLEAN NOT NULL DEFAULT TRUE,
                        enable_course_update BOOLEAN NOT NULL DEFAULT TRUE,
                        enable_project_review BOOLEAN NOT NULL DEFAULT TRUE,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_notification_preferences_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """))

        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "notification_templates" not in table_names:
            if conn.dialect.name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE notification_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code VARCHAR(64) NOT NULL UNIQUE,
                        category VARCHAR(32) NOT NULL DEFAULT 'system',
                        title_template VARCHAR(256) NOT NULL,
                        content_template TEXT NOT NULL DEFAULT '',
                        action_url_template VARCHAR(512) NOT NULL DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE notification_templates (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        code VARCHAR(64) NOT NULL UNIQUE,
                        category VARCHAR(32) NOT NULL DEFAULT 'system',
                        title_template VARCHAR(256) NOT NULL,
                        content_template TEXT NOT NULL,
                        action_url_template VARCHAR(512) NOT NULL DEFAULT '',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            conn.execute(text("CREATE INDEX ix_notification_templates_code ON notification_templates (code)"))
            conn.execute(text("CREATE INDEX ix_notification_templates_category ON notification_templates (category)"))

        # 通知模板：新库建表或旧库补表后，幂等补齐默认模板。
        if "notification_templates" in inspect(conn).get_table_names():
            default_templates = [
                {
                    "code": "assignment_due_soon",
                    "category": "assignment",
                    "title_template": "作业《$title》即将截止",
                    "content_template": "请及时完成作业，避免错过截止时间。",
                    "action_url_template": "/practice/announcement/$announcement_id",
                },
                {
                    "code": "grade_published",
                    "category": "grade",
                    "title_template": "成绩已发布",
                    "content_template": "你有新的成绩通知，请及时查看。",
                    "action_url_template": "/profile",
                },
                {
                    "code": "course_material_added",
                    "category": "course",
                    "title_template": "课程资料已更新",
                    "content_template": "课程《$course_name》新增了学习资料。",
                    "action_url_template": "/learn/course/$course_id",
                },
                {
                    "code": "project_rejected",
                    "category": "project",
                    "title_template": "作品《$project_title》审核未通过",
                    "content_template": "$reason",
                    "action_url_template": "/projects/$project_id",
                },
            ]
            for template in default_templates:
                exists = conn.execute(
                    text("SELECT 1 FROM notification_templates WHERE code = :code"),
                    {"code": template["code"]},
                ).first()
                if exists:
                    continue
                conn.execute(text("""
                    INSERT INTO notification_templates (code, category, title_template, content_template, action_url_template)
                    VALUES (:code, :category, :title_template, :content_template, :action_url_template)
                """), template)

        # ── task_completions 表：作业评分字段 ──────────────────────────────
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "task_completions" in table_names:
            _add_column_if_missing(conn, inspector, "task_completions", "score", "FLOAT NULL")
            _add_column_if_missing(conn, inspector, "task_completions", "max_score", "FLOAT NOT NULL DEFAULT 100.0")

        # ── announcements 表：作业满分配置 ──────────────────────────────────
        inspector = inspect(conn)
        if "announcements" in table_names:
            _add_column_if_missing(conn, inspector, "announcements", "max_score", "FLOAT NOT NULL DEFAULT 100.0")
            json_type = "JSON NULL" if conn.dialect.name == "mysql" else "TEXT"
            _add_column_if_missing(conn, inspector, "announcements", "question_scores", json_type)

        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "audit_logs" not in table_names:
            if conn.dialect.name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(32),
                        user_role VARCHAR(16),
                        action VARCHAR(64) NOT NULL,
                        resource_type VARCHAR(32),
                        resource_id VARCHAR(64),
                        resource_name VARCHAR(256),
                        details TEXT,
                        ip_address VARCHAR(64),
                        user_agent VARCHAR(512),
                        status VARCHAR(16) NOT NULL DEFAULT 'success',
                        error_message VARCHAR(512),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE audit_logs (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(32) NULL,
                        user_role VARCHAR(16) NULL,
                        action VARCHAR(64) NOT NULL,
                        resource_type VARCHAR(32) NULL,
                        resource_id VARCHAR(64) NULL,
                        resource_name VARCHAR(256) NULL,
                        details JSON NULL,
                        ip_address VARCHAR(64) NULL,
                        user_agent VARCHAR(512) NULL,
                        status VARCHAR(16) NOT NULL DEFAULT 'success',
                        error_message VARCHAR(512) NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_audit_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                    )
                """))
            conn.execute(text("CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id)"))
            conn.execute(text("CREATE INDEX ix_audit_logs_action ON audit_logs (action)"))
            conn.execute(text("CREATE INDEX ix_audit_logs_resource_type ON audit_logs (resource_type)"))
            conn.execute(text("CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at)"))
        elif conn.dialect.name != "sqlite":
            try:
                conn.execute(text("ALTER TABLE audit_logs MODIFY COLUMN resource_id VARCHAR(64) NULL"))
            except Exception:
                pass


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


def _ensure_course_name_owner_unique(conn, inspector) -> None:
    """兼容旧库 courses.name 全局唯一约束，改为同一教师下唯一。"""
    if conn.dialect.name != "mysql":
        return
    if "courses" not in {t for t in inspector.get_table_names()}:
        return

    indexes = inspector.get_indexes("courses")
    for index in indexes:
        if index.get("unique") and index.get("column_names") == ["name"]:
            conn.execute(text(f"ALTER TABLE courses DROP INDEX {index['name']}"))

    has_owner_unique = any(
        index.get("unique") and index.get("column_names") == ["name", "created_by"]
        for index in inspector.get_indexes("courses")
    )
    if not has_owner_unique:
        conn.execute(text("ALTER TABLE courses ADD UNIQUE KEY uq_course_name_created_by (name, created_by)"))


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


def _ensure_check_constraint(conn, inspector, table: str, name: str, expression: str) -> None:
    """为 MySQL 表补充 CHECK 约束；SQLite 测试库由模型新建无需处理。"""
    if conn.dialect.name != "mysql":
        return
    table_names = {t for t in inspector.get_table_names()}
    if table not in table_names:
        return
    try:
        constraints = conn.execute(text(
            "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND CONSTRAINT_NAME = :name"
        ), {"table": table, "name": name}).fetchall()
        if not constraints:
            conn.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression})"))
    except Exception:
        # MySQL 版本不支持 CHECK 约束时静默跳过
        pass
