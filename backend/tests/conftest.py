"""测试配置：SQLite 内存数据库 + FastAPI TestClient"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.core.security import get_password_hash
from app.models.entities import User, Chapter, Question, Class, StudentClassEnrollment, Course


@pytest.fixture(scope="function")
def db_session():
    """创建独立的 SQLite 内存数据库会话"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()

    # 种子测试数据
    _seed_test_data(session)

    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _seed_test_data(session):
    """插入测试所需的最小种子数据"""
    # 用户
    student = User(id="2025001", name="测试学生", hashed_password=get_password_hash("abc123"), role="student", major="自动化专业")
    teacher = User(id="T001", name="测试教师", hashed_password=get_password_hash("abc123"), role="teacher", major="")
    session.add_all([student, teacher])

    # 课程
    course = Course(name="测试课程")
    session.add(course)
    session.flush()

    # 章节
    chapter = Chapter(num="01", title="测试章节", desc="测试", status="已发布", sort_order=1, course_id=course.id)
    session.add(chapter)
    session.flush()

    # 班级 + 注册
    cls = Class(name="2025级1班", major="自动化专业")
    session.add(cls)
    session.flush()
    session.add(StudentClassEnrollment(user_id="2025001", class_id=cls.id))

    # 题目
    q = Question(type="choice", chapter_id=chapter.id, stem="1+1=?", options=["A. 1", "B. 2", "C. 3", "D. 4"], answer="B", explanation="基础加法")
    session.add(q)

    session.commit()


@pytest.fixture(scope="function")
def client(db_session):
    """返回带测试数据库的 FastAPI TestClient"""
    from main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def student_token(client):
    """学生登录获取 token"""
    resp = client.post("/api/token", json={"id": "2025001", "password": "abc123"})
    return resp.json()["data"]["access_token"]


@pytest.fixture(scope="function")
def teacher_token(client):
    """教师登录获取 token"""
    resp = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    return resp.json()["data"]["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}
