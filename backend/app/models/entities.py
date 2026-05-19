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

    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("StudentProgress", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="author", cascade="all, delete-orphan")
    likes = relationship("ProjectLike", back_populates="user", cascade="all, delete-orphan")
    enrollments = relationship("StudentClassEnrollment", back_populates="user", cascade="all, delete-orphan")


class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    major = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    enrollments = relationship("StudentClassEnrollment", back_populates="class_", cascade="all, delete-orphan")


class StudentClassEnrollment(Base):
    __tablename__ = "student_class_enrollment"
    __table_args__ = (UniqueConstraint("user_id", "class_id", name="uq_student_class_enrollment"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="enrollments")
    class_ = relationship("Class", back_populates="enrollments")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    chapters = relationship("Chapter", back_populates="course", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    num = Column(String(8), unique=True, nullable=False)
    title = Column(String(64), nullable=False)
    desc = Column(String(256), default="")
    topics = Column(JSON, default=list)
    status = Column(String(16), default="已发布")
    sort_order = Column(Integer, default=0)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    day_of_week = Column(String(16), default="")
    class_periods = Column(String(32), default="")
    schedule_note = Column(String(128), default="")

    course = relationship("Course", back_populates="chapters")
    materials = relationship("Material", back_populates="chapter", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="chapter", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    type = Column(String(16), nullable=False)
    title = Column(String(128), nullable=False)
    url = Column(String(512), default="")
    duration = Column(String(16), default="")
    pages = Column(Integer, default=0)
    size = Column(String(32), default="0 MB")
    date = Column(String(32), default="")

    chapter = relationship("Chapter", back_populates="materials")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(16), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    stem = Column(Text, nullable=False)
    options = Column(JSON, default=list)
    answer = Column(String(128), nullable=False)
    explanation = Column(Text, default="")

    chapter = relationship("Chapter", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    user_answer = Column(String(128), default="")
    is_correct = Column(Boolean, default=False)
    answered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="quiz_attempts")
    question = relationship("Question")


class StudentProgress(Base):
    __tablename__ = "student_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    learn_progress = Column(Integer, default=0)
    questions_done = Column(Integer, default=0)
    accuracy = Column(Integer, default=0)

    user = relationship("User", back_populates="progress")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    author_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
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

    author = relationship("User", back_populates="projects")
    project_likes = relationship("ProjectLike", back_populates="project", cascade="all, delete-orphan")


class ProjectLike(Base):
    __tablename__ = "project_likes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    user = relationship("User", back_populates="likes")
    project = relationship("Project", back_populates="project_likes")


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(16), nullable=False)
    title = Column(String(128), nullable=False)
    content = Column(Text, default="")
    question_ids = Column(JSON, default=list)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    class_ = relationship("Class")
    teacher = relationship("User")
    reads = relationship("AnnouncementRead", back_populates="announcement", cascade="all, delete-orphan")
    completions = relationship("TaskCompletion", back_populates="announcement", cascade="all, delete-orphan")


class AnnouncementRead(Base):
    __tablename__ = "announcement_reads"
    __table_args__ = (UniqueConstraint("user_id", "announcement_id", name="uq_announcement_reads"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    announcement_id = Column(Integer, ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False, index=True)
    read_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    announcement = relationship("Announcement", back_populates="reads")
    user = relationship("User")


class TaskCompletion(Base):
    __tablename__ = "task_completions"
    __table_args__ = (UniqueConstraint("announcement_id", "user_id", name="uq_task_completions"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    announcement_id = Column(Integer, ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    announcement = relationship("Announcement", back_populates="completions")
    user = relationship("User")


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(32), nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(String(256), default="")
