from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.services import agent_runs_service
from app.database import get_db
from app.schemas.agent_runs import (
    AgentEventsPage,
    AgentRunCreateRequest,
    AgentRunCreateResponse,
    AgentRunRead,
    RunStatus,
)

router = APIRouter()


@router.post("", response_model=AgentRunCreateResponse)
def create_agent_run(payload: AgentRunCreateRequest, db: Session = Depends(get_db)):
    return agent_runs_service.create_agent_run(payload, db)


@router.post("/start", response_model=AgentRunCreateResponse)
def start_agent_run(
    payload: AgentRunCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return agent_runs_service.start_agent_run(payload, background_tasks, db)


@router.get("/{run_id}", response_model=AgentRunRead)
def get_agent_run(run_id: str, db: Session = Depends(get_db)):
    return agent_runs_service.get_agent_run(run_id, db)


@router.get("/{run_id}/events", response_model=AgentEventsPage)
def list_agent_events(
    run_id: str,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return agent_runs_service.list_agent_events(run_id, after_seq, limit, db)


@router.get("/{run_id}/events/stream")
def stream_agent_events(
    run_id: str,
    request: Request,
    after_seq: int = Query(default=0, ge=0),
    poll_interval_s: float = Query(default=0.25, ge=0.05, le=5.0),
    db: Session = Depends(get_db),
):
    return agent_runs_service.stream_agent_events(run_id, request, after_seq, poll_interval_s, db)


@router.post("/{run_id}/execute")
def execute_agent_run(run_id: str, db: Session = Depends(get_db)):
    return agent_runs_service.execute_agent_run(run_id, db)


@router.get("", response_model=list[AgentRunRead])
def list_agent_runs(
    agent_name: Optional[str] = Query(
        default=None, description="Optional filter (e.g. 'vitals_agent')."
    ),
    status: Optional[RunStatus] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    return agent_runs_service.list_agent_runs(
        agent_name=agent_name,
        status=status,
        limit=limit,
        offset=offset,
        order=order,
        db=db,
    )
