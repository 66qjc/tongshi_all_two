"""测试配置：SQLite 内存数据库 + FastAPI TestClient"""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.session import Base, get_db
from app.models.entities import Class, Course, Question, StudentClassEnrollment, User


@pytest.fixture(autouse=True)
def force_local_storage_for_tests(monkeypatch, request):
    """测试环境强制 local 存储，避免依赖外部对象存储服务。"""
    safe_name = request.node.nodeid.replace("\\", "_").replace("/", "_").replace(":", "_")
    upload_dir = Path(__file__).resolve().parents[1] / ".test-uploads" / safe_name
    upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("app.core.config.settings.storage_backend", "local")
    monkeypatch.setattr("app.core.config.settings.local_upload_dir", str(upload_dir))

    from app.services.storage_local import LocalStorageAdapter
    import app.services.file_service as file_service

    monkeypatch.setattr(file_service, "_local_adapter", LocalStorageAdapter(upload_dir))
    yield
    shutil.rmtree(upload_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def db_session():
    """创建隔离的 SQLite 内存数据库会话。"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()

    _seed_test_data(session)

    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _seed_test_data(session):
    """插入测试所需的最小种子数据。"""
    student = User(
        id="2025001",
        name="测试学生",
        hashed_password=get_password_hash("abc123"),
        role="student",
        major="自动化专业",
    )
    other_student = User(
        id="2025002",
        name="其它学生",
        hashed_password=get_password_hash("abc123"),
        role="student",
        major="人工智能",
    )
    teacher = User(
        id="T001",
        name="测试教师",
        hashed_password=get_password_hash("abc123"),
        role="teacher",
        major="",
    )
    other_teacher = User(
        id="T002",
        name="其它教师",
        hashed_password=get_password_hash("abc123"),
        role="teacher",
        major="",
    )
    admin = User(
        id="admin",
        name="管理员",
        hashed_password=get_password_hash("Admin#2026"),
        role="admin",
        major="",
    )
    session.add_all([student, other_student, teacher, other_teacher, admin])

    course = Course(name="测试课程", created_by="T001")
    other_course = Course(name="其它课程", created_by="T002")
    session.add_all([course, other_course])
    session.flush()

    cls = Class(name="2025级1班", course_id=course.id, created_by="T001")
    other_cls = Class(name="2025级2班", course_id=other_course.id, created_by="T002")
    session.add_all([cls, other_cls])
    session.flush()

    session.add(StudentClassEnrollment(user_id="2025001", class_id=cls.id))
    session.add(StudentClassEnrollment(user_id="2025002", class_id=other_cls.id))

    q = Question(
        type="choice",
        course_id=course.id,
        stem="1+1=?",
        options=["A. 1", "B. 2", "C. 3", "D. 4"],
        answer="B",
        explanation="基础加法",
    )
    session.add(q)

    session.commit()


@pytest.fixture(scope="function")
def client(db_session):
    """返回带测试数据库的 FastAPI TestClient。"""
    from main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app, raise_server_exceptions=True)
    yield c
    c.close()
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def student_token(client):
    """学生登录获取 token。"""
    resp = client.post("/api/token", json={"id": "2025001", "password": "abc123"})
    return resp.json()["data"]["access_token"]


@pytest.fixture(scope="function")
def teacher_token(client):
    """教师登录获取 token。"""
    resp = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    return resp.json()["data"]["access_token"]


@pytest.fixture(scope="function")
def other_teacher_token(client):
    """其它教师登录获取 token。"""
    resp = client.post("/api/token", json={"id": "T002", "password": "abc123"})
    return resp.json()["data"]["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}
