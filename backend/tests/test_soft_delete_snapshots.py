from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

from app.core.timezone_utils import BEIJING_TZ
from app.db import schema_compat
from app.db.schema_compat import ensure_schema_compatibility
from app.models.entities import HistorySnapshot, Question
from app.services.history_snapshot_service import capture_snapshot, list_snapshots
from app.services.soft_delete_policy import retention_deadline


def test_resource_retention_policy_uses_calendar_months():
    deleted_at = datetime(2026, 1, 15, 3, 0, tzinfo=BEIJING_TZ)
    assert retention_deadline(deleted_at, "courses") == datetime(
        2026, 2, 14, 3, 0, tzinfo=BEIJING_TZ
    )
    assert retention_deadline(deleted_at, "materials") == datetime(
        2026, 7, 15, 3, 0, tzinfo=BEIJING_TZ
    )


def test_snapshot_has_no_foreign_keys_and_preserves_chinese_payload(db_session):
    snapshot = capture_snapshot(
        db_session,
        resource_type="announcements",
        resource_id=7,
        fact_type="答题记录",
        fact_id=11,
        snapshot_kind="答题记录",
        payload={"作业标题": "第一次作业", "题目ID": 3, "学生姓名": "测试学生"},
    )
    db_session.commit()
    assert snapshot.resource_id == "7"
    assert snapshot.payload["作业标题"] == "第一次作业"
    assert snapshot.__table__.foreign_keys == set()


def test_snapshot_query_survives_source_row_delete(db_session):
    question = db_session.query(Question).first()
    capture_snapshot(
        db_session,
        resource_type="questions",
        resource_id=question.id,
        fact_type="答题记录",
        fact_id=21,
        snapshot_kind="答题记录",
        payload={"题干": "历史题目"},
    )
    db_session.delete(question)
    db_session.commit()
    assert list_snapshots(
        db_session, resource_type="questions", resource_id=question.id
    )


def test_duplicate_fact_snapshot_is_idempotent(db_session):
    first = capture_snapshot(
        db_session,
        resource_type="questions",
        resource_id=1,
        fact_type="答题记录",
        fact_id=42,
        snapshot_kind="答题记录",
        payload={"题干": "第一次"},
    )
    second = capture_snapshot(
        db_session,
        resource_type="questions",
        resource_id=1,
        fact_type="答题记录",
        fact_id=42,
        snapshot_kind="答题记录",
        payload={"题干": "第二次"},
    )
    db_session.commit()

    assert second.id == first.id
    assert db_session.query(HistorySnapshot).count() == 1
    assert list_snapshots(db_session, fact_type="答题记录", fact_id=42)[0]["payload"]["题干"] == "第一次"


def test_history_snapshot_indexes_are_present(db_session):
    indexes = {index["name"] for index in inspect(db_session.bind).get_indexes("history_snapshots")}
    assert "ix_history_snapshots_resource" in indexes
    assert "uq_history_snapshots_fact" in indexes
    assert "ix_history_snapshots_cleanup_batch" in indexes
    assert "ix_history_snapshots_captured_at" in indexes


def test_schema_compatibility_creates_history_snapshots_for_old_sqlite_database():
    engine = create_engine("sqlite:///:memory:")
    try:
        ensure_schema_compatibility(engine)
        inspector = inspect(engine)
        assert "history_snapshots" in inspector.get_table_names()
        indexes = {index["name"] for index in inspector.get_indexes("history_snapshots")}
        assert {
            "ix_history_snapshots_resource",
            "uq_history_snapshots_fact",
            "ix_history_snapshots_cleanup_batch",
            "ix_history_snapshots_captured_at",
        }.issubset(indexes)

        ensure_schema_compatibility(engine)
    finally:
        engine.dispose()


def test_history_snapshot_schema_compatibility_does_not_hide_mysql_ddl_errors(monkeypatch):
    class ExistingHistorySnapshotInspector:
        def get_table_names(self):
            return ["history_snapshots"]

        def get_indexes(self, _table_name):
            return []

    class FailingMySQLConnection:
        dialect = SimpleNamespace(name="mysql")

        def execute(self, _statement):
            raise OperationalError("CREATE INDEX", {}, RuntimeError("DDL permission denied"))

    monkeypatch.setattr(schema_compat, "inspect", lambda _conn: ExistingHistorySnapshotInspector())

    with pytest.raises(OperationalError, match="DDL permission denied"):
        schema_compat._ensure_history_snapshot_table(FailingMySQLConnection())


def _as_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def test_teacher_reports_read_history_after_assignment_cleanup(db_session):
    """作业到期清理后，教师成绩列表/完成报告/导出/档案仍可读历史数值。"""
    from app.models.entities import (
        Announcement,
        AnnouncementClass,
        Class,
        Course,
        Project,
        Question,
        QuizAttempt,
        StudentClassEnrollment,
        TaskCompletion,
        User,
    )
    from app.services.portfolio_service import get_portfolio
    from app.services.soft_delete_cleanup_service import cleanup_expired_resources
    from app.services.task_service import completion_report
    from app.services.teacher_service import build_student_task_score_export, list_students

    deleted_at = datetime(2026, 1, 10, 3, 0, tzinfo=BEIJING_TZ)
    cleanup_now = datetime(2026, 2, 15, 3, 0, tzinfo=BEIJING_TZ)

    course = Course(name="历史报表课", created_by="T001")
    db_session.add(course)
    db_session.flush()
    cls = Class(name="历史1班", course_id=course.id, created_by="T001")
    db_session.add(cls)
    db_session.flush()
    # 复用种子学生，确保 list_students 能查到
    enrollment = (
        db_session.query(StudentClassEnrollment)
        .filter(StudentClassEnrollment.user_id == "2025001")
        .first()
    )
    if enrollment is None:
        db_session.add(StudentClassEnrollment(user_id="2025001", class_id=cls.id, import_order=1))
    else:
        enrollment.class_id = cls.id

    question = Question(
        course_id=course.id,
        type="choice",
        stem="历史题干",
        options=["A", "B"],
        answer="A",
        created_by="T001",
    )
    db_session.add(question)
    db_session.flush()
    assignment = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="quiz",
        title="清理前作业",
        question_ids=[question.id],
        deleted_at=_as_utc_naive(deleted_at),
        deleted_by="T001",
    )
    db_session.add(assignment)
    db_session.flush()
    db_session.add(AnnouncementClass(announcement_id=assignment.id, class_id=cls.id))
    db_session.add(
        QuizAttempt(
            user_id="2025001",
            question_id=question.id,
            announcement_id=assignment.id,
            user_answer="A",
            is_correct=True,
        )
    )
    db_session.add(
        TaskCompletion(
            user_id="2025001",
            announcement_id=assignment.id,
            score=100,
            max_score=100,
        )
    )
    project = Project(
        title="历史作品",
        author_id="2025001",
        course_id=course.id,
        major="自动化专业",
        description="清理前作品",
        tags=["历史"],
        likes=3,
        featured=True,
        status="approved",
        date="2026-01-01",
        video_url="https://example.com/video.mp4",
        report_url="https://example.com/report.pdf",
        image_url="https://example.com/cover.png",
        deleted_at=_as_utc_naive(datetime(2025, 7, 15, 3, 0, tzinfo=BEIJING_TZ)),
        deleted_by="2025001",
    )
    db_session.add(project)
    db_session.commit()
    assignment_id = assignment.id
    project_id = project.id

    result = cleanup_expired_resources(db_session, now=cleanup_now)
    assert result["cleaned_count"] >= 1
    assert db_session.get(Announcement, assignment_id) is None
    assert db_session.get(Project, project_id) is None

    students, total = list_students(db_session, teacher_id="T001", course_id=course.id)
    assert total >= 1
    student_row = next(item for item in students if item["id"] == "2025001")
    assert student_row["completed_tasks"] >= 1
    assert any(
        score_item["announcement_id"] == assignment_id and score_item["score"] == 100
        for score_item in student_row["task_scores"]
    )

    report = completion_report(db_session, announcement_id=assignment_id, teacher_id="T001")
    assert report is not None
    assert report["completed_count"] >= 1
    assert report["source"] == "history_snapshot"
    assert report.get("detail_url", "") == ""
    completed_ids = {item["id"] for item in report["completed_students"]["items"]}
    assert "2025001" in completed_ids
    score = next(
        item["score"] for item in report["completed_students"]["items"] if item["id"] == "2025001"
    )
    assert score == 100

    export_groups = build_student_task_score_export(
        db_session, teacher_id="T001", course_id=course.id
    )
    assert export_groups
    group = next(item for item in export_groups if item["course_id"] == course.id)
    assert any(task["id"] == assignment_id for task in group["tasks"])
    export_student = next(item for item in group["students"] if item["id"] == "2025001")
    assert export_student["scores"].get(assignment_id) == 100

    portfolio = get_portfolio(db_session, "2025001")
    assert portfolio is not None
    assert portfolio["stats"]["total_exercises"] >= 1
    assert portfolio["stats"]["project_count"] >= 1
    history_project = next(item for item in portfolio["projects"] if item["id"] == project_id)
    assert history_project["title"] == "历史作品"
    assert history_project.get("video_url", "") == ""
    assert history_project.get("report_url", "") == ""
    assert history_project.get("image_url", "") == ""


def test_audit_log_returns_chinese_action_name(db_session):
    """审计日志查询应返回中文动作名，且保留内部 action 代码。"""
    from app.models.entities import AuditLog
    from app.services.audit_service import export_audit_logs, query_audit_logs

    db_session.add(
        AuditLog(
            user_id="T001",
            user_role="teacher",
            action="course.delete",
            resource_type="courses",
            resource_id="1",
            resource_name="测试课程",
            status="success",
            details={"级联删除子资源": {"班级": 1}},
        )
    )
    db_session.commit()

    data = query_audit_logs(db_session, action="course.delete")
    assert data["total"] >= 1
    item = data["items"][0]
    assert item["action"] == "course.delete"
    assert item["action_name"] == "删除课程"
    assert item["resource_type_name"] == "课程"
    assert item["status_name"] == "成功"

    content, count = export_audit_logs(db_session, action="course.delete")
    assert count >= 1
    assert isinstance(content, (bytes, bytearray))
    assert b"action" not in content  # 导出为 xlsx 二进制，至少保证可生成
