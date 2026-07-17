"""软删除到期快照与自动清理回归测试。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.timezone_utils import BEIJING_TZ
from app.models.entities import (
    Announcement,
    AnnouncementClass,
    AnnouncementRead,
    AuditLog,
    Class,
    Course,
    HistorySnapshot,
    Material,
    MaterialPreview,
    Project,
    ProjectImage,
    ProjectLike,
    Question,
    QuizAttempt,
    StoredFile,
    StudentClassEnrollment,
    TaskCompletion,
    User,
)
from app.services.soft_delete_policy import retention_deadline


FIXED_SUNDAY = datetime(2026, 2, 15, 3, 0, tzinfo=BEIJING_TZ)


def _as_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def seed_deleted_course(db_session, deleted_at: datetime) -> Course:
    operator = User(id="TCLN", name="清理教师", hashed_password="hash", role="teacher")
    course = Course(
        name="到期清理课程",
        created_by="TCLN",
        deleted_at=_as_utc_naive(deleted_at),
        deleted_by="TCLN",
    )
    db_session.add_all([operator, course])
    db_session.flush()
    cls = Class(
        name="同批班级",
        course_id=course.id,
        created_by="TCLN",
        deleted_at=_as_utc_naive(deleted_at),
        deleted_by="TCLN",
    )
    material = Material(
        course_id=course.id,
        type="link",
        title="同批资料",
        url="https://example.com/batch",
        deleted_at=_as_utc_naive(deleted_at),
        deleted_by="TCLN",
    )
    announcement = Announcement(
        course_id=course.id,
        teacher_id="TCLN",
        type="quiz",
        title="同批作业",
        question_ids=[],
        deleted_at=_as_utc_naive(deleted_at),
        deleted_by="TCLN",
    )
    db_session.add_all([cls, material, announcement])
    db_session.commit()
    return course


def seed_expired_material(db_session, *, deleted_at: datetime | None = None) -> Material:
    deleted_at = deleted_at or datetime(2025, 7, 15, 3, 0, tzinfo=BEIJING_TZ)
    course = Course(name="资料清理课", created_by="T001")
    db_session.add(course)
    db_session.flush()
    stored = StoredFile(
        object_key="materials/expired.pdf",
        original_name="到期资料.pdf",
        stored_name="expired.pdf",
        created_by="T001",
    )
    db_session.add(stored)
    db_session.flush()
    material = Material(
        course_id=course.id,
        type="pdf",
        title="到期资料",
        url="/materials/expired.pdf",
        file_id=stored.id,
        deleted_at=_as_utc_naive(deleted_at),
        deleted_by="T001",
    )
    db_session.add(material)
    db_session.flush()
    preview = MaterialPreview(material_id=material.id, status="ready", cover_file_id=None)
    db_session.add(preview)
    db_session.commit()
    return material


def latest_audit(db_session) -> AuditLog:
    return db_session.query(AuditLog).order_by(AuditLog.id.desc()).first()


def test_cleanup_runs_only_after_retention_and_next_sunday(db_session):
    from app.services.soft_delete_cleanup_service import cleanup_expired_resources

    deleted_at = datetime(2026, 1, 15, 3, 0, tzinfo=BEIJING_TZ)
    course = seed_deleted_course(db_session, deleted_at)
    assert retention_deadline(deleted_at, "courses") == datetime(2026, 2, 14, 3, 0, tzinfo=BEIJING_TZ)

    early = cleanup_expired_resources(
        db_session,
        now=datetime(2026, 2, 14, 2, 59, tzinfo=BEIJING_TZ),
    )
    assert early.get("cleaned_count", 0) == 0
    assert db_session.get(Course, course.id) is not None

    result = cleanup_expired_resources(
        db_session,
        now=datetime(2026, 2, 15, 3, 0, tzinfo=BEIJING_TZ),
    )
    assert result["cleaned_count"] >= 1
    assert db_session.get(Course, course.id) is None


def test_cleanup_failure_is_audited_and_retryable(db_session, monkeypatch):
    from app.services.soft_delete_cleanup_service import cleanup_expired_resources

    material = seed_expired_material(db_session)

    def fail_file_delete(*_args, **_kwargs):
        raise OSError("文件删除失败")

    monkeypatch.setattr(
        "app.services.soft_delete_cleanup_service._delete_file_if_unreferenced",
        fail_file_delete,
    )
    result = cleanup_expired_resources(db_session, now=FIXED_SUNDAY)
    assert result["failed_count"] == 1
    audit = latest_audit(db_session)
    assert audit is not None
    assert "文件删除失败" in (audit.details or {}).get("失败原因", "")
    assert db_session.query(Material).filter(Material.deleted_at.isnot(None)).count() == 1
    assert db_session.get(Material, material.id) is not None


def test_question_cleanup_snapshots_attempts_before_physical_delete(db_session):
    from app.services.soft_delete_cleanup_service import cleanup_expired_resources

    course = Course(name="题目清理课", created_by="T001")
    db_session.add(course)
    db_session.flush()
    question = Question(
        course_id=course.id,
        type="choice",
        stem="到期题目",
        options=["A", "B"],
        answer="A",
        created_by="T001",
        deleted_at=_as_utc_naive(datetime(2025, 7, 15, 3, 0, tzinfo=BEIJING_TZ)),
        deleted_by="admin",
    )
    db_session.add(question)
    db_session.flush()
    assignment = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="quiz",
        title="历史作业",
        question_ids=[question.id],
        deleted_at=_as_utc_naive(datetime(2025, 7, 15, 3, 0, tzinfo=BEIJING_TZ)),
        deleted_by="T001",
    )
    db_session.add(assignment)
    db_session.flush()
    attempt = QuizAttempt(
        user_id="2025001",
        question_id=question.id,
        announcement_id=assignment.id,
        user_answer="A",
        is_correct=True,
    )
    db_session.add(attempt)
    db_session.commit()
    attempt_id = attempt.id
    question_id = question.id

    result = cleanup_expired_resources(db_session, now=FIXED_SUNDAY)
    assert result["cleaned_count"] >= 1
    assert db_session.get(Question, question_id) is None
    assert db_session.get(QuizAttempt, attempt_id) is None
    snapshots = db_session.query(HistorySnapshot).filter(
        HistorySnapshot.resource_type == "questions",
        HistorySnapshot.resource_id == str(question_id),
    ).all()
    assert snapshots
    assert any(row.fact_type == "答题记录" for row in snapshots)


def test_course_cleanup_only_removes_same_batch_children(db_session):
    """非同批已软删资料在课程清理时脱钩保留，课程可物理删除。"""
    from app.services.soft_delete_cleanup_service import cleanup_expired_resources

    deleted_at = datetime(2026, 1, 15, 3, 0, tzinfo=BEIJING_TZ)
    course = seed_deleted_course(db_session, deleted_at)
    separate = Material(
        course_id=course.id,
        type="link",
        title="独立删除资料",
        url="https://example.com/separate",
        deleted_at=_as_utc_naive(deleted_at - timedelta(days=1)),
        deleted_by="T001",
    )
    db_session.add(separate)
    db_session.commit()
    separate_id = separate.id
    course_id = course.id

    result = cleanup_expired_resources(db_session, now=FIXED_SUNDAY)
    assert result["cleaned_count"] >= 1
    assert db_session.get(Course, course_id) is None
    detached = db_session.get(Material, separate_id)
    assert detached is not None
    assert detached.course_id is None
    assert detached.deleted_at is not None


def test_public_purge_does_not_participate_in_cleanup(db_session):
    from app.core.exceptions import BusinessException
    from app.schemas.common import AuthUser
    from app.services.soft_delete_service import purge_resource

    course = Course(
        name="不可手动purge",
        created_by="T001",
        deleted_at=_as_utc_naive(datetime(2025, 1, 1, tzinfo=BEIJING_TZ)),
        deleted_by="admin",
    )
    db_session.add(course)
    db_session.commit()
    with pytest.raises(BusinessException) as exc:
        purge_resource(db_session, "courses", str(course.id), AuthUser(id="admin", name="", role="admin"))
    assert exc.value.code == 403
    assert db_session.get(Course, course.id) is not None


def test_course_cleanup_detaches_shared_questions_instead_of_deleting_them(db_session):
    """共享题挂载在到期课时：课程可清理，题目保留并脱钩。"""
    from app.services.soft_delete_cleanup_service import cleanup_expired_resources

    deleted_at = datetime(2026, 1, 15, 3, 0, tzinfo=BEIJING_TZ)
    course = seed_deleted_course(db_session, deleted_at)
    question = Question(
        course_id=course.id,
        type="choice",
        stem="仍挂载在到期课上的共享题",
        options=["A", "B"],
        answer="A",
        created_by="TCLN",
        mount_course_name_snapshot="",
    )
    db_session.add(question)
    db_session.commit()
    question_id = question.id
    course_id = course.id
    course_name = course.name

    result = cleanup_expired_resources(db_session, now=FIXED_SUNDAY)
    assert result["cleaned_count"] >= 1
    assert db_session.get(Course, course_id) is None
    surviving = db_session.get(Question, question_id)
    assert surviving is not None
    assert surviving.deleted_at is None
    assert surviving.course_id is None
    assert surviving.mount_course_name_snapshot == course_name


def test_orm_delete_course_does_not_delete_shared_questions(db_session):
    """Course.questions 不得再带 delete-orphan，ORM 删除课程不能误删共享题。"""
    course = Course(name="ORM删除课", created_by="T001")
    db_session.add(course)
    db_session.flush()
    question = Question(
        course_id=course.id,
        type="fill",
        stem="不应被 ORM 级联删除",
        options=[],
        answer="A",
        created_by="T001",
    )
    db_session.add(question)
    db_session.commit()
    question_id = question.id
    course_id = course.id

    row = db_session.get(Course, course_id)
    db_session.delete(row)
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()
        # SQLite 未开 FK 时可能仍删课成功；无论是否成功，题都必须还在
    assert db_session.get(Question, question_id) is not None


def test_course_cleanup_with_sqlite_foreign_keys_enabled():
    """开启 SQLite 外键后，课程 cleanup 仍应脱钩共享题/作品并删课。"""
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db.session import Base
    from app.core.security import get_password_hash
    from app.services.soft_delete_cleanup_service import cleanup_expired_resources

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        # 确认外键已开启
        enabled = session.execute(text("PRAGMA foreign_keys")).scalar()
        assert int(enabled or 0) == 1

        teacher = User(
            id="T_FK",
            name="外键教师",
            hashed_password=get_password_hash("abc123"),
            role="teacher",
        )
        student = User(
            id="S_FK",
            name="外键学生",
            hashed_password=get_password_hash("abc123"),
            role="student",
        )
        session.add_all([teacher, student])
        session.flush()

        deleted_at = datetime(2026, 1, 15, 3, 0, tzinfo=BEIJING_TZ)
        course = Course(
            name="SQLite外键清理课",
            created_by="T_FK",
            deleted_at=_as_utc_naive(deleted_at),
            deleted_by="T_FK",
        )
        session.add(course)
        session.flush()
        course_id = course.id
        course_name = course.name

        cls = Class(
            name="同批班级",
            course_id=course.id,
            created_by="T_FK",
            deleted_at=_as_utc_naive(deleted_at),
            deleted_by="T_FK",
        )
        material = Material(
            course_id=course.id,
            type="link",
            title="同批资料",
            url="https://example.com/fk-batch",
            deleted_at=_as_utc_naive(deleted_at),
            deleted_by="T_FK",
        )
        announcement = Announcement(
            course_id=course.id,
            teacher_id="T_FK",
            type="quiz",
            title="同批作业",
            question_ids=[],
            deleted_at=_as_utc_naive(deleted_at),
            deleted_by="T_FK",
        )
        question = Question(
            course_id=course.id,
            type="fill",
            stem="外键开启后应脱钩",
            options=[],
            answer="A",
            created_by="T_FK",
            mount_course_name_snapshot="",
        )
        project = Project(
            title="外键开启后作品保留",
            description="x",
            author_id="S_FK",
            course_id=course.id,
            status="approved",
        )
        session.add_all([cls, material, announcement, question, project])
        session.commit()
        question_id = question.id
        project_id = project.id

        result = cleanup_expired_resources(session, now=FIXED_SUNDAY)
        assert result["cleaned_count"] >= 1
        assert session.get(Course, course_id) is None

        surviving_q = session.get(Question, question_id)
        assert surviving_q is not None
        assert surviving_q.course_id is None
        assert surviving_q.deleted_at is None
        assert surviving_q.mount_course_name_snapshot == course_name

        surviving_p = session.get(Project, project_id)
        assert surviving_p is not None
        assert surviving_p.course_id is None

        # 系统清理审计不得依赖不存在的 system 用户行
        audit = session.query(AuditLog).order_by(AuditLog.id.desc()).first()
        assert audit is not None
        assert audit.user_id is None
        assert audit.user_role == "system"
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_detached_material_restore_requires_target_course(db_session):
    """脱钩资料直接恢复失败；指定活跃目标课后恢复成功。"""
    from app.schemas.common import AuthUser
    from app.core.exceptions import BusinessException
    from app.services.soft_delete_service import restore_resource

    target = Course(name="恢复目标课", created_by="admin", is_public=True)
    material = Material(
        course_id=None,
        type="link",
        title="已脱钩资料",
        url="https://example.com/detached",
        deleted_at=_as_utc_naive(datetime(2026, 1, 1, 0, 0, tzinfo=BEIJING_TZ)),
        deleted_by="admin",
    )
    db_session.add_all([target, material])
    db_session.commit()
    material_id = material.id
    target_id = target.id
    operator = AuthUser(id="admin", name="管理员", role="admin")

    with pytest.raises(BusinessException) as exc:
        restore_resource(db_session, "materials", str(material_id), operator)
    assert exc.value.code == 400
    assert "原课程已清理" in exc.value.message

    result = restore_resource(
        db_session,
        "materials",
        str(material_id),
        operator,
        target_course_id=target_id,
    )
    restored = db_session.get(Material, material_id)
    assert restored is not None
    assert restored.deleted_at is None
    assert restored.course_id == target_id
    assert result.get("重新挂载课程ID") == target_id


def test_cleanup_cli_entry_returns_nonzero_on_failure(monkeypatch):
    import importlib.util
    from pathlib import Path

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_soft_delete_cleanup.py"
    spec = importlib.util.spec_from_file_location("run_soft_delete_cleanup", script_path)
    cli = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(cli)

    class DummySession:
        def close(self):
            return None

    monkeypatch.setattr(cli, "SessionLocal", lambda: DummySession())

    def boom(*_args, **_kwargs):
        return {"cleaned_count": 0, "failed_count": 2}

    monkeypatch.setattr(cli, "cleanup_expired_resources", boom)
    code = cli.main([])
    assert code != 0
