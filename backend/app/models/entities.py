"""Database models"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
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

    quiz_attempts = relationship(
        "QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    progress = relationship(
        "StudentProgress", back_populates="user", cascade="all, delete-orphan")
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    course = relationship("Course", back_populates="classes")
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
    enrolled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="enrollments")
    class_ = relationship("Class", back_populates="enrollments")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("name", "created_by", name="uq_course_name_created_by"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    created_by = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    creator = relationship("User", foreign_keys=[created_by])
    classes = relationship("Class", back_populates="course", cascade="all, delete-orphan")
    materials = relationship(
        "Material", back_populates="course", cascade="all, delete-orphan")
    questions = relationship(
        "Question", back_populates="course", cascade="all, delete-orphan")
    progress = relationship(
        "StudentProgress", back_populates="course", cascade="all, delete-orphan")


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
    file_id = Column(Integer, ForeignKey(
        "stored_files.id"), nullable=True, index=True)

    course = relationship("Course", back_populates="materials")


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

    course = relationship("Course", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey(
        "users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey(
        "questions.id"), nullable=False, index=True)
    user_answer = Column(String(128), default="")
    is_correct = Column(Boolean, default=False)
    answered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="quiz_attempts")
    question = relationship("Question")


class StudentProgress(Base):
    __tablename__ = "student_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey(
        "users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey(
        "courses.id"), nullable=False, index=True)
    learn_progress = Column(Integer, default=0)
    questions_done = Column(Integer, default=0)
    accuracy = Column(Integer, default=0)

    user = relationship("User", back_populates="progress")
    course = relationship("Course", back_populates="progress")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    author_id = Column(String(32), ForeignKey(
        "users.id"), nullable=False, index=True)
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

    author = relationship("User", back_populates="projects")
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

    announcement = relationship("Announcement", back_populates="completions")
    user = relationship("User")


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(32), nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(String(256), default="")


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
    content = Column(Text, default="")
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
