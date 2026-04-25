from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.swarm_event import SwarmEvent


def append_event(
    db: Session,
    *,
    swarm_run_id: str,
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
    ev = SwarmEvent(
        swarm_run_id=swarm_run_id,
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


def get_last_event_seq(db: Session, swarm_run_id: str) -> int:
    stmt = (
        select(SwarmEvent.seq)
        .where(SwarmEvent.swarm_run_id == swarm_run_id)
        .order_by(SwarmEvent.seq.desc())
        .limit(1)
    )
    last = db.execute(stmt).scalar_one_or_none()
    return int(last) if last is not None else 0


def list_events_after(
    db: Session,
    *,
    swarm_run_id: str,
    after_seq: int,
    limit: int,
) -> list[SwarmEvent]:
    stmt = (
        select(SwarmEvent)
        .where(SwarmEvent.swarm_run_id == swarm_run_id, SwarmEvent.seq > after_seq)
        .order_by(SwarmEvent.seq.asc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def rollback(db: Session) -> None:
    db.rollback()
