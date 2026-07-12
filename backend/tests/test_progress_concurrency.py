"""课时进度并发写入回归测试。"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.entities import (
    Class,
    Course,
    CourseProgress,
    Lesson,
    LessonProgress,
    StudentClassEnrollment,
    User,
)
from app.schemas.common import AuthUser, LessonProgressIn
from app.services import progress_service


def _seed_progress_database(url: str, connect_args: dict | None = None) -> tuple[str, int, int]:
    """创建并发测试所需的独立学生、课程和课时。"""
    engine = create_engine(url, connect_args=connect_args or {})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    suffix = uuid4().hex[:10]
    student_id = f"progress-{suffix}"
    teacher_id = f"teacher-progress-{suffix}"

    with SessionLocal() as session:
        session.add_all([
            User(id=student_id, name="并发学生", hashed_password="unused", role="student"),
            User(id=teacher_id, name="并发教师", hashed_password="unused", role="teacher"),
        ])
        session.flush()
        course = Course(name=f"并发进度课程-{suffix}", created_by=teacher_id)
        session.add(course)
        session.flush()
        class_ = Class(name=f"并发进度班级-{suffix}", course_id=course.id, created_by=teacher_id)
        lesson = Lesson(course_id=course.id, title="并发课时", status="published")
        session.add_all([class_, lesson])
        session.flush()
        session.add(StudentClassEnrollment(user_id=student_id, class_id=class_.id))
        session.commit()
        course_id = course.id
        lesson_id = lesson.id

    engine.dispose()
    return student_id, course_id, lesson_id


def _cleanup_progress_database(url: str, student_id: str, course_id: int, connect_args: dict | None = None) -> None:
    """清理可复用 MySQL 测试库中的并发用例数据。"""
    engine = create_engine(url, connect_args=connect_args or {})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with SessionLocal() as session:
        class_ids = [
            row[0]
            for row in session.query(Class.id).filter(Class.course_id == course_id).all()
        ]
        session.query(LessonProgress).filter(LessonProgress.user_id == student_id).delete(
            synchronize_session=False,
        )
        session.query(CourseProgress).filter(CourseProgress.user_id == student_id).delete(
            synchronize_session=False,
        )
        if class_ids:
            session.query(StudentClassEnrollment).filter(
                StudentClassEnrollment.class_id.in_(class_ids),
            ).delete(synchronize_session=False)
        session.query(Lesson).filter(Lesson.course_id == course_id).delete(synchronize_session=False)
        session.query(Class).filter(Class.course_id == course_id).delete(synchronize_session=False)
        session.query(Course).filter(Course.id == course_id).delete(synchronize_session=False)
        session.query(User).filter(User.id == student_id).delete(synchronize_session=False)
        session.query(User).filter(User.id.like("teacher-progress-%")).delete(synchronize_session=False)
        session.commit()
    engine.dispose()


def _assert_concurrent_first_reports(
    url: str,
    monkeypatch: pytest.MonkeyPatch,
    connect_args: dict | None = None,
) -> None:
    """断言两个独立会话首次上报时不会丢数据或创建重复行。"""
    student_id, course_id, lesson_id = _seed_progress_database(url, connect_args)
    engine_a = create_engine(url, connect_args=connect_args or {})
    engine_b = create_engine(url, connect_args=connect_args or {})
    SessionA = sessionmaker(bind=engine_a, autocommit=False, autoflush=False)
    SessionB = sessionmaker(bind=engine_b, autocommit=False, autoflush=False)
    start_barrier = Barrier(2)
    service_barrier = Barrier(2)
    current_user = AuthUser(id=student_id, name="并发学生", role="student")

    def synchronized_now() -> datetime:
        service_barrier.wait(timeout=10)
        return datetime.now(timezone.utc)

    def worker(SessionLocal, duration_seconds: int) -> None:
        with SessionLocal() as session:
            start_barrier.wait(timeout=10)
            progress_service.report_lesson_progress(
                session,
                course_id,
                lesson_id,
                LessonProgressIn(
                    progress_percent=25,
                    duration_seconds=duration_seconds,
                    visit_started=True,
                ),
                current_user,
            )
            session.commit()

    try:
        with monkeypatch.context() as patch:
            patch.setattr(progress_service, "_utc_now", synchronized_now)
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(worker, SessionA, 11),
                    executor.submit(worker, SessionB, 13),
                ]
                for future in futures:
                    future.result(timeout=20)

        verify_engine = create_engine(url, connect_args=connect_args or {})
        VerifySession = sessionmaker(bind=verify_engine, autocommit=False, autoflush=False)
        with VerifySession() as session:
            lesson_rows = session.query(LessonProgress).filter(
                LessonProgress.user_id == student_id,
                LessonProgress.lesson_id == lesson_id,
            ).all()
            course_rows = session.query(CourseProgress).filter(
                CourseProgress.user_id == student_id,
                CourseProgress.course_id == course_id,
            ).all()

            assert len(lesson_rows) == 1
            assert lesson_rows[0].duration_seconds == 24
            assert lesson_rows[0].view_count == 2
            assert len(course_rows) == 1
            assert course_rows[0].last_lesson_id == lesson_id
        verify_engine.dispose()
    finally:
        engine_a.dispose()
        engine_b.dispose()
        _cleanup_progress_database(url, student_id, course_id, connect_args)


def test_concurrent_first_reports_are_atomic_on_sqlite(tmp_path, monkeypatch):
    """SQLite 首次并发上报应原子创建并累加。"""
    url = f"sqlite:///{tmp_path / 'progress-concurrency.db'}"
    _assert_concurrent_first_reports(
        url,
        monkeypatch,
        {"check_same_thread": False, "timeout": 20},
    )


@pytest.mark.skipif(not os.getenv("TEST_MYSQL_URL"), reason="未配置 TEST_MYSQL_URL")
def test_concurrent_first_reports_are_atomic_on_mysql(monkeypatch):
    """配置 MySQL 测试库时重复验证同一并发语义。"""
    _assert_concurrent_first_reports(os.environ["TEST_MYSQL_URL"], monkeypatch)
