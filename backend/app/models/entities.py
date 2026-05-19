"""Database models"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String(32), primary_key=True)
    name = Column(String(64), nullable=False)
    hashed_password = Column(String(128), nullable=False)
    role = Column(String(16), nullable=False, default="student")  # student | teacher
    major = Column(String(64), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("StudentProgress", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="author", cascade="all, delete-orphan")
    likes = relationship("ProjectLike", back_populates="user", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    num = Column(String(8), unique=True, nullable=False)
    title = Column(String(64), nullable=False)
    desc = Column(String(256), default="")
    topics = Column(JSON, default=list)
    status = Column(String(16), default="已发布")  # 已发布 | 即将发布
    sort_order = Column(Integer, default=0)

    materials = relationship("Material", back_populates="chapter", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="chapter", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    type = Column(String(16), nullable=False)  # video | pdf
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
    type = Column(String(16), nullable=False)  # choice | fill
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    stem = Column(Text, nullable=False)
    options = Column(JSON, default=list)  # ["A. xxx", "B. xxx", ...]
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


class StudentProgress(Base):
    __tablename__ = "student_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    learn_progress = Column(Integer, default=0)  # 0-100
    questions_done = Column(Integer, default=0)
    accuracy = Column(Integer, default=0)  # 0-100

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
    status = Column(String(16), default="pending")  # pending | approved | rejected
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


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(32), nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(String(256), default="")
