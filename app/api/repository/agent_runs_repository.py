from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_event import AgentEvent
from app.models.agent_run import AgentRun
from app.schemas.agent_runs import RunStatus


def get_run(db: Session, run_id: str) -> Optional[AgentRun]:
    return db.get(AgentRun, run_id)


def save_run(db: Session, run: AgentRun, *, refresh: bool = False) -> None:
    db.add(run)
    db.commit()
    if refresh:
        db.refresh(run)


def list_runs(
    db: Session,
    *,
    agent_name: Optional[str],
    status: Optional[RunStatus],
    limit: int,
    offset: int,
    order: str,
) -> list[AgentRun]:
    stmt = select(AgentRun)

    if agent_name:
        stmt = stmt.where(AgentRun.agent_name == agent_name)
    if status:
        stmt = stmt.where(AgentRun.status == status)

    if order == "asc":
        stmt = stmt.order_by(AgentRun.created_at.asc(), AgentRun.id.asc())
    else:
        stmt = stmt.order_by(AgentRun.created_at.desc(), AgentRun.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


def append_event(
    db: Session,
    *,
    run_id: str,
    agent_name: str,
    seq: int,
    event_type: str,
    node_name: Optional[str] = None,
    tool_name: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    status: Optional[str] = None,
    payload_json: Optional[dict] = None,
    payload_text: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> None:
    ev = AgentEvent(
        run_id=run_id,
        agent_name=agent_name,
        seq=seq,
        event_type=event_type,
        node_name=node_name,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        status=status,
        payload_json=payload_json,
        payload_text=payload_text,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(ev)
    db.commit()


def get_last_event_seq(db: Session, run_id: str) -> int:
    stmt = (
        select(AgentEvent.seq)
        .where(AgentEvent.run_id == run_id)
        .order_by(AgentEvent.seq.desc())
        .limit(1)
    )
    last = db.execute(stmt).scalar_one_or_none()
    return int(last) if last is not None else 0


def list_events_after(
    db: Session,
    *,
    run_id: str,
    after_seq: int,
    limit: int,
) -> list[AgentEvent]:
    stmt = (
        select(AgentEvent)
        .where(AgentEvent.run_id == run_id, AgentEvent.seq > after_seq)
        .order_by(AgentEvent.seq.asc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def rollback(db: Session) -> None:
    db.rollback()
