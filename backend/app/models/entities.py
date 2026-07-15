"""Database models"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String(32), primary_key=True)
    name = Column(String(64), nullable=False)
    hashed_password = Column(String(128), nullable=False)
    role = Column(String(16), nullable=False, default="student")
    major = Column(String(64), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    needs_password_change = Column(Boolean, nullable=False, default=False)
    # 每次改密时递增，用于使旧 JWT 立即失效
    token_version = Column(Integer, nullable=False, default=0)
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(32), nullable=True, index=True)

    quiz_attempts = relationship(
        "QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    projects = relationship(
        "Project", back_populates="author", cascade="all, delete-orphan")
    likes = relationship("ProjectLike", back_populates="user",
                         cascade="all, delete-orphan")
    enrollments = relationship(
        "StudentClassEnrollment", back_populates="user", cascade="all, delete-orphan")


class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    created_by = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(32), nullable=True, index=True)

    course = relationship("Course", back_populates="classes")
    creator = relationship("User", foreign_keys=[created_by])
    enrollments = relationship(
        "StudentClassEnrollment", back_populates="class_", cascade="all, delete-orphan")


class StudentClassEnrollment(Base):
    __tablename__ = "student_class_enrollment"
    __table_args__ = (UniqueConstraint("user_id", "class_id",
                      name="uq_student_class_enrollment"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey(
        "classes.id", ondelete="CASCADE"), nullable=False, index=True)
    import_order = Column(Integer, nullable=False, default=0)
    enrolled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="enrollments")
    class_ = relationship("Class", back_populates="enrollments")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("name", "created_by", name="uq_course_name_created_by"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    created_by = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    is_public = Column(Boolean, nullable=False, default=False, index=True)
    source_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    question_bank_root_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(32), nullable=True, index=True)

    creator = relationship("User", foreign_keys=[created_by])
    classes = relationship("Class", back_populates="course", cascade="all, delete-orphan")
    stages = relationship(
        "CourseStage", back_populates="course", cascade="all, delete-orphan",
        order_by="CourseStage.sort_order")
    materials = relationship(
        "Material", back_populates="course", cascade="all, delete-orphan")
    questions = relationship(
        "Question", back_populates="course", cascade="all, delete-orphan")
    lessons = relationship(
        "Lesson", back_populates="course", cascade="all, delete-orphan",
        order_by="Lesson.sort_order")


class CourseStage(Base):
    """课程阶段/目录"""
    __tablename__ = "course_stages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    source_stage_id = Column(Integer, ForeignKey("course_stages.id"), nullable=True, index=True)
    name = Column(String(64), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    course = relationship("Course", back_populates="stages")
    materials = relationship("Material", back_populates="stage")


class Lesson(Base):
    """课程课时（学习页面图文一体）"""
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey(
        "courses.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    status = Column(Enum("draft", "published"), nullable=False, default="published")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    course = relationship("Course", back_populates="lessons")


class CourseProgress(Base):
    """课程学习进度"""
    __tablename__ = "course_progress"
    __table_args__ = (UniqueConstraint(
        "user_id", "course_id", name="uq_course_progress_user_course"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey(
        "courses.id", ondelete="CASCADE"), nullable=False, index=True)
    last_lesson_id = Column(Integer, ForeignKey(
        "lessons.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User")
    course = relationship("Course")
    last_lesson = relationship("Lesson")


class LessonProgress(Base):
    """课时级学习进度。"""
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
        Index("ix_lesson_progress_user_course", "user_id", "course_id"),
        Index("ix_lesson_progress_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey(
        "courses.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey(
        "lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="not_started")
    progress_percent = Column(Integer, nullable=False, default=0)
    last_position = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=False, default=0)
    first_viewed_at = Column(DateTime, nullable=True)
    last_viewed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, nullable=False, default=0)

    user = relationship("User")
    course = relationship("Course")
    lesson = relationship("Lesson")


class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey(
        "courses.id"), nullable=False, index=True)
    type = Column(String(16), nullable=False)
    title = Column(String(128), nullable=False)
    url = Column(String(512), default="")
    duration = Column(String(16), default="")
    pages = Column(Integer, default=0)
    size = Column(String(32), default="0 MB")
    date = Column(String(32), default="")
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(32), nullable=True, index=True)
    file_id = Column(Integer, ForeignKey(
        "stored_files.id"), nullable=True, index=True)
    source_material_id = Column(Integer, ForeignKey(
        "materials.id"), nullable=True, index=True)
    stage_id = Column(Integer, ForeignKey(
        "course_stages.id", ondelete="SET NULL"), nullable=True, index=True)

    course = relationship("Course", back_populates="materials")
    stage = relationship("CourseStage", back_populates="materials")
    preview = relationship(
        "MaterialPreview",
        back_populates="material",
        uselist=False,
        cascade="all, delete-orphan",
    )


class MaterialPreview(Base):
    """课程资料预览元数据。"""
    __tablename__ = "material_previews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(String(16), nullable=False, default="pending")
    cover_file_id = Column(Integer, ForeignKey("stored_files.id"), nullable=True, index=True)
    summary = Column(Text, default="")
    page_count = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=False, default=0)
    resolution = Column(String(32), default="")
    error_message = Column(String(256), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    material = relationship("Material", back_populates="preview")
    cover_file = relationship("StoredFile", foreign_keys=[cover_file_id])


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(16), nullable=False)
    course_id = Column(Integer, ForeignKey(
        "courses.id"), nullable=False, index=True)
    stem = Column(Text, nullable=False)
    options = Column(JSON, default=list)
    answer = Column(String(128), nullable=False)
    explanation = Column(Text, default="")
    tags = Column(JSON, default=list)
    source_question_id = Column(Integer, ForeignKey(
        "questions.id"), nullable=True, index=True)
    # 题库优化字段
    created_by = Column(String(32), ForeignKey("users.id"), nullable=True, index=True)
    star_rating = Column(Integer, nullable=False, default=3)  # 1-5星，默认3星
    stem_hash = Column(String(64), nullable=True, index=True)  # 题干MD5，用于防重复
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(32), nullable=True, index=True)

    course = relationship("Course", back_populates="questions")
    creator = relationship("User", foreign_keys=[created_by])


class QuestionContributionLog(Base):
    """公共课程题库贡献记录。"""
    __tablename__ = "question_contribution_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_course_id = Column(Integer, nullable=False, index=True)
    public_course_name = Column(String(128), nullable=False, default="")
    operator_id = Column(String(32), nullable=False, index=True)
    operator_name = Column(String(64), nullable=False, default="")
    operator_role = Column(String(16), nullable=False, default="")
    action = Column(String(16), nullable=False, index=True)
    question_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        # 高频联合查询：按用户+任务聚合，用于任务完成度统计
        Index("ix_quiz_attempt_user_ann", "user_id", "announcement_id"),
        # 高频联合查询：按用户+题目聚合，用于错题本和答题统计
        Index("ix_quiz_attempt_user_question", "user_id", "question_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey(
        "users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey(
        "questions.id", ondelete="CASCADE"), nullable=False, index=True)
    announcement_id = Column(Integer, ForeignKey(
        "announcements.id", ondelete="CASCADE"), nullable=True, index=True)
    user_answer = Column(String(128), default="")
    is_correct = Column(Boolean, default=False)
    answered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="quiz_attempts")
    question = relationship("Question")
    announcement = relationship("Announcement")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    author_id = Column(String(32), ForeignKey(
        "users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    major = Column(String(64), default="")
    description = Column(Text, default="")
    tags = Column(JSON, default=list)
    likes = Column(Integer, default=0)
    featured = Column(Boolean, default=False)
    video_url = Column(String(512), default="")
    report_url = Column(String(512), default="")
    image_url = Column(String(512), default="")
    link_url = Column(String(512), default="")
    status = Column(String(16), default="pending")
    reject_reason = Column(String(256), default="")
    date = Column(String(32), default="")
    report_file_id = Column(Integer, ForeignKey(
        "stored_files.id"), nullable=True, index=True)
    cover_file_id = Column(Integer, ForeignKey(
        "stored_files.id"), nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(32), nullable=True, index=True)

    author = relationship("User", back_populates="projects")
    course = relationship("Course")
    images = relationship(
        "ProjectImage",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectImage.sort_order",
    )
    project_likes = relationship(
        "ProjectLike", back_populates="project", cascade="all, delete-orphan")


class ProjectImage(Base):
    __tablename__ = "project_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey(
        "projects.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String(512), nullable=False, default="")
    sort_order = Column(Integer, nullable=False, default=0)
    file_id = Column(Integer, ForeignKey(
        "stored_files.id"), nullable=True, index=True)

    project = relationship("Project", back_populates="images")


class ProjectLike(Base):
    __tablename__ = "project_likes"
    __table_args__ = (UniqueConstraint("user_id", "project_id", name="uq_project_like"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey(
        "users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey(
        "projects.id"), nullable=False, index=True)

    user = relationship("User", back_populates="likes")
    project = relationship("Project", back_populates="project_likes")


class StudentNotification(Base):
    __tablename__ = "student_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(32), nullable=False, default="project_review")
    title = Column(String(128), nullable=False)
    content = Column(Text, default="")
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    category = Column(String(32), nullable=False, default="project", index=True)
    priority = Column(String(16), nullable=False, default="normal", index=True)
    action_url = Column(String(512), default="")
    extra_data = Column(JSON, default=dict)
    expires_at = Column(DateTime, nullable=True, index=True)
    sent_at = Column(DateTime, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    project = relationship("Project")


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey(
        "classes.id", ondelete="CASCADE"), nullable=True, index=True)
    course_id = Column(Integer, ForeignKey(
        "courses.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(String(32), ForeignKey(
        "users.id"), nullable=False, index=True)
    type = Column(String(16), nullable=False)
    title = Column(String(128), nullable=False)
    content = Column(Text, default="")
    question_ids = Column(JSON, default=list)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(32), nullable=True, index=True)
    # 作业评分配置
    max_score = Column(Float, nullable=False, default=100.0)  # 作业满分
    question_scores = Column(JSON, nullable=True)  # 每题分值配置 {question_id: score}

    class_ = relationship("Class")
    course = relationship("Course")
    teacher = relationship("User")
    target_classes = relationship(
        "AnnouncementClass", back_populates="announcement", cascade="all, delete-orphan")
    reads = relationship(
        "AnnouncementRead", back_populates="announcement", cascade="all, delete-orphan")
    completions = relationship(
        "TaskCompletion", back_populates="announcement", cascade="all, delete-orphan")


class AnnouncementClass(Base):
    __tablename__ = "announcement_classes"
    __table_args__ = (UniqueConstraint(
        "announcement_id", "class_id", name="uq_announcement_class"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    announcement_id = Column(Integer, ForeignKey(
        "announcements.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey(
        "classes.id", ondelete="CASCADE"), nullable=False, index=True)

    announcement = relationship("Announcement", back_populates="target_classes")
    class_ = relationship("Class")


class AnnouncementRead(Base):
    __tablename__ = "announcement_reads"
    __table_args__ = (UniqueConstraint(
        "user_id", "announcement_id", name="uq_announcement_reads"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    announcement_id = Column(Integer, ForeignKey(
        "announcements.id", ondelete="CASCADE"), nullable=False, index=True)
    read_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    announcement = relationship("Announcement", back_populates="reads")
    user = relationship("User")


class TaskCompletion(Base):
    __tablename__ = "task_completions"
    __table_args__ = (UniqueConstraint("announcement_id",
                      "user_id", name="uq_task_completions"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    announcement_id = Column(Integer, ForeignKey(
        "announcements.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(32), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    # 作业评分字段
    score = Column(Float, nullable=True)  # 最终得分（百分制）
    max_score = Column(Float, nullable=False, default=100.0)  # 满分

    announcement = relationship("Announcement", back_populates="completions")
    user = relationship("User")




class StoredFile(Base):
    __tablename__ = "stored_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    biz_type = Column(String(32), nullable=False, default="")
    biz_id = Column(Integer, nullable=True, index=True)
    storage_provider = Column(String(16), nullable=False, default="local")
    bucket_name = Column(String(128), default="")
    object_key = Column(String(512), nullable=False, default="")
    original_name = Column(String(255), nullable=False, default="")
    stored_name = Column(String(255), nullable=False, default="")
    content_type = Column(String(128), default="")
    extension = Column(String(32), default="")
    size_bytes = Column(Integer, nullable=False, default=0)
    sha256 = Column(String(64), default="")
    status = Column(String(16), nullable=False, default="active")
    created_by = Column(String(32), ForeignKey(
        "users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ShowcaseItem(Base):
    """悟页面图文展示内容"""
    __tablename__ = "showcase_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # "welfare" | "reading_club"
    section = Column(String(32), nullable=False)
    title = Column(String(128), nullable=False)
    content = Column(Text, default="")  # 纯文本摘要，用于列表预览与旧版回退
    # 有序内容块（图文混排）：[{type:text,data:{text}}, {type:image,data:{file_id,caption}}]
    content_blocks = Column(JSON, nullable=True)
    cover_file_id = Column(Integer, ForeignKey(
        "stored_files.id"), nullable=True)
    link_url = Column(String(512), default="")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(32), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(
        timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    cover_file = relationship("StoredFile", foreign_keys=[cover_file_id])
    creator = relationship("User", foreign_keys=[created_by])
    images = relationship("ShowcaseItemImage", back_populates="showcase_item",
                          cascade="all, delete-orphan", order_by="ShowcaseItemImage.sort_order")


class ShowcaseItemImage(Base):
    """悟页面图文内容的多张图片"""
    __tablename__ = "showcase_item_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    showcase_item_id = Column(Integer, ForeignKey(
        "showcase_items.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey(
        "stored_files.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    showcase_item = relationship("ShowcaseItem", back_populates="images")
    file = relationship("StoredFile")


class SecurityQuestion(Base):
    """用户密保问题"""
    __tablename__ = "security_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(String(200), nullable=False)
    answer_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class PasswordResetRequest(Base):
    """密码重置申请（人工审批）"""
    __tablename__ = "password_reset_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending / approved / rejected
    resolved_by = Column(String(32), ForeignKey("users.id"), nullable=True, index=True)
    new_password_hash = Column(String(255), nullable=True)
    temp_password = Column(String(32), nullable=True)  # 审批时生成的临时密码明文（学生首次登录后即改）
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    applicant = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])


class NotificationPreference(Base):
    """学生通知偏好设置。"""
    __tablename__ = "notification_preferences"

    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    enable_assignment_due = Column(Boolean, nullable=False, default=True)
    enable_grade_published = Column(Boolean, nullable=False, default=True)
    enable_course_update = Column(Boolean, nullable=False, default=True)
    enable_project_review = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class NotificationTemplate(Base):
    """通知模板。"""
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    category = Column(String(32), nullable=False, default="system", index=True)
    title_template = Column(String(256), nullable=False)
    content_template = Column(Text, nullable=False, default="")
    action_url_template = Column(String(512), nullable=False, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    """系统审计日志。"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_role = Column(String(16), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(32), nullable=True, index=True)
    resource_id = Column(String(64), nullable=True, index=True)
    resource_name = Column(String(256), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    status = Column(String(16), nullable=False, default="success", index=True)
    error_message = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User")


class HistorySnapshot(Base):
    """Immutable, foreign-key-free facts retained after resource cleanup."""

    __tablename__ = "history_snapshots"
    __table_args__ = (
        Index("ix_history_snapshots_resource", "resource_type", "resource_id"),
        Index("uq_history_snapshots_fact", "fact_type", "fact_id", unique=True),
        Index("ix_history_snapshots_cleanup_batch", "cleanup_batch_id"),
        Index("ix_history_snapshots_captured_at", "captured_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_type = Column(String(32), nullable=False)
    resource_id = Column(String(64), nullable=False)
    fact_type = Column(String(64), nullable=False)
    fact_id = Column(String(64), nullable=False)
    snapshot_kind = Column(String(64), nullable=False)
    cleanup_batch_id = Column(String(64), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    captured_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
