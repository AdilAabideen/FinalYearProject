"""Mas Events Repository repository helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.mas_event import MASEvent


def append_event(
    db: Session,
    *,
    mas_run_id: str,
    seq: int,
    event_type: str,
    workflow_id: Optional[str] = None,
    agent_run_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    handoff_id: Optional[str] = None,
    gate_evaluation_id: Optional[str] = None,
    final_output_id: Optional[str] = None,
    status: Optional[str] = None,
    payload_json: Optional[dict] = None,
    payload_text: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> None:
    """Append event."""
    # Keep the next value explicit.
    ev = MASEvent(
        mas_run_id=mas_run_id,
        seq=seq,
        event_type=event_type,
        workflow_id=workflow_id,
        agent_run_id=agent_run_id,
        agent_name=agent_name,
        handoff_id=handoff_id,
        gate_evaluation_id=gate_evaluation_id,
        final_output_id=final_output_id,
        status=status,
        payload_json=payload_json,
        payload_text=payload_text,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(ev)
    db.commit()


def get_last_event_seq(db: Session, mas_run_id: str) -> int:
    """Return last event seq."""
    # Read the current value.
    stmt = (
        select(MASEvent.seq)
        .where(MASEvent.mas_run_id == mas_run_id)
        .order_by(MASEvent.seq.desc())
        .limit(1)
    )
    last = db.execute(stmt).scalar_one_or_none()
    return int(last) if last is not None else 0


def list_events_after(
    db: Session,
    *,
    mas_run_id: str,
    after_seq: int,
    limit: int,
) -> list[MASEvent]:
    """List events after."""
    # Read the current list.
    stmt = (
        select(MASEvent)
        .where(MASEvent.mas_run_id == mas_run_id, MASEvent.seq > after_seq)
        .order_by(MASEvent.seq.asc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def rollback(db: Session) -> None:
    """Handle the value."""
    # Keep the main step clear.
    db.rollback()


def count_events_for_mas(db: Session, *, mas_run_id: str) -> int:
    """Count events for MAS."""
    # Derive the needed value.
    stmt = select(func.count()).select_from(MASEvent).where(MASEvent.mas_run_id == mas_run_id)
    return int(db.execute(stmt).scalar_one())
