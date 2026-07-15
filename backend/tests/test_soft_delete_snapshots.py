from datetime import datetime

from sqlalchemy import inspect

from app.core.timezone_utils import BEIJING_TZ
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
