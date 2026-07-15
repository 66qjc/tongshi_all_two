"""Read/write helpers for immutable history snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import HistorySnapshot


def capture_snapshot(
    db: Session,
    resource_type: str,
    resource_id: str | int,
    fact_type: str,
    fact_id: str | int,
    snapshot_kind: str,
    payload: dict[str, Any],
    cleanup_batch_id: str | None = None,
) -> HistorySnapshot:
    """Insert one snapshot, returning the existing row for duplicate facts.

    This function deliberately flushes but never commits, leaving transaction
    ownership with the caller.
    """

    normalized_fact_type = str(fact_type)
    normalized_fact_id = str(fact_id)
    existing = (
        db.query(HistorySnapshot)
        .filter(
            HistorySnapshot.fact_type == normalized_fact_type,
            HistorySnapshot.fact_id == normalized_fact_id,
        )
        .first()
    )
    if existing is not None:
        return existing

    now = datetime.now(timezone.utc)
    snapshot = HistorySnapshot(
        resource_type=str(resource_type),
        resource_id=str(resource_id),
        fact_type=normalized_fact_type,
        fact_id=normalized_fact_id,
        snapshot_kind=str(snapshot_kind),
        cleanup_batch_id=str(cleanup_batch_id) if cleanup_batch_id is not None else None,
        payload=dict(payload),
        captured_at=now,
        created_at=now,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def list_snapshots(
    db: Session,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
    cleanup_batch_id: str | None = None,
    fact_type: str | None = None,
    fact_id: str | int | None = None,
) -> list[dict[str, Any]]:
    """Read snapshots as detached dictionaries, optionally filtered."""

    query = db.query(HistorySnapshot)
    if resource_type is not None:
        query = query.filter(HistorySnapshot.resource_type == str(resource_type))
    if resource_id is not None:
        query = query.filter(HistorySnapshot.resource_id == str(resource_id))
    if cleanup_batch_id is not None:
        query = query.filter(HistorySnapshot.cleanup_batch_id == str(cleanup_batch_id))
    if fact_type is not None:
        query = query.filter(HistorySnapshot.fact_type == str(fact_type))
    if fact_id is not None:
        query = query.filter(HistorySnapshot.fact_id == str(fact_id))

    rows = query.order_by(HistorySnapshot.captured_at.asc(), HistorySnapshot.id.asc()).all()
    return [
        {
            "id": row.id,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "fact_type": row.fact_type,
            "fact_id": row.fact_id,
            "snapshot_kind": row.snapshot_kind,
            "cleanup_batch_id": row.cleanup_batch_id,
            "payload": dict(row.payload or {}),
            "captured_at": row.captured_at,
            "created_at": row.created_at,
        }
        for row in rows
    ]
