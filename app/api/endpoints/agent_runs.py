from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.agent_event import AgentEvent
from app.models.agent_run import AgentRun
from app.schemas.agent_runs import (
    AgentEventsPage,
    AgentEventRead,
    AgentRunCreateRequest,
    AgentRunCreateResponse,
    AgentRunRead,
)

router = APIRouter()

SUPPORTED_AGENTS = {"vitals_agent"}


@router.post("", response_model=AgentRunCreateResponse)
def create_agent_run(payload: AgentRunCreateRequest, db: Session = Depends(get_db)):
    if payload.agent_name not in SUPPORTED_AGENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported agent_name '{payload.agent_name}'. Supported: {sorted(SUPPORTED_AGENTS)}",
        )

    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = AgentRun(
        id=run_id,
        agent_name=payload.agent_name,
        status="created",
        model_name=settings.OPENAI_MODEL,
        input_json=payload.input,
        started_at=None,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(run)
    db.commit()

    return AgentRunCreateResponse(run_id=run_id, status="created")


@router.get("/{run_id}", response_model=AgentRunRead)
def get_agent_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return AgentRunRead.model_validate(run.__dict__)


@router.get("/{run_id}/events", response_model=AgentEventsPage)
def list_agent_events(
    run_id: str,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    stmt = (
        select(AgentEvent)
        .where(AgentEvent.run_id == run_id, AgentEvent.seq > after_seq)
        .order_by(AgentEvent.seq.asc())
        .limit(limit)
    )
    events = db.execute(stmt).scalars().all()
    items = [AgentEventRead.model_validate(e.__dict__) for e in events]
    next_after_seq = items[-1].seq if items else after_seq
    return AgentEventsPage(run_id=run_id, events=items, next_after_seq=next_after_seq)

