from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.services import swarm_events_service, swarm_query_service, swarm_runs_service
from app.database import get_db
from app.schemas.swarm_read import (
    SwarmAgentRunRead,
    SwarmFinalOutputRead,
    SwarmGateEvaluationRead,
    SwarmHandoffRead,
    SwarmRunMetricsRead,
    SwarmSummaryRead,
)
from app.schemas.swarm_events import SwarmEventsPage
from app.schemas.swarm_runs import (
    SwarmRunCreateRequest,
    SwarmRunCreateResponse,
    SwarmRunFinalizeRequest,
    SwarmRunRead,
    SwarmRunStatus,
    SwarmRunUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=SwarmRunCreateResponse)
def create_swarm_run(payload: SwarmRunCreateRequest, db: Session = Depends(get_db)):
    return swarm_runs_service.create_swarm_run(payload, db)


@router.post("/{swarm_run_id}/start", response_model=SwarmRunRead)
def start_swarm_run(swarm_run_id: str, db: Session = Depends(get_db)):
    return swarm_runs_service.start_swarm_run(swarm_run_id, db)


@router.patch("/{swarm_run_id}", response_model=SwarmRunRead)
def update_swarm_run(
    swarm_run_id: str,
    payload: SwarmRunUpdateRequest,
    db: Session = Depends(get_db),
):
    return swarm_runs_service.update_swarm_run(
        swarm_run_id,
        db,
        status=payload.status,
        current_agent_run_id=payload.current_agent_run_id,
        current_gate_id=payload.current_gate_id,
        final_output_json=payload.final_output_json,
        error_text=payload.error_text,
        metadata_json=payload.metadata_json,
    )


@router.post("/{swarm_run_id}/finalize", response_model=SwarmRunRead)
def finalize_swarm_run(
    swarm_run_id: str,
    payload: SwarmRunFinalizeRequest,
    db: Session = Depends(get_db),
):
    return swarm_runs_service.finalize_swarm_run(
        swarm_run_id,
        db,
        status=payload.status,
        final_output_json=payload.final_output_json,
        error_text=payload.error_text,
        current_agent_run_id=payload.current_agent_run_id,
        current_gate_id=payload.current_gate_id,
    )


@router.get("/{swarm_run_id}/events", response_model=SwarmEventsPage)
def list_swarm_events(
    swarm_run_id: str,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return swarm_events_service.list_swarm_events(swarm_run_id, after_seq, limit, db)


@router.get("/{swarm_run_id}/events/stream")
def stream_swarm_events(
    swarm_run_id: str,
    request: Request,
    after_seq: int = Query(default=0, ge=0),
    poll_interval_s: float = Query(default=0.25, ge=0.05, le=5.0),
    db: Session = Depends(get_db),
):
    return swarm_events_service.stream_swarm_events(swarm_run_id, request, after_seq, poll_interval_s, db)


@router.get("/{swarm_run_id}/summary", response_model=SwarmSummaryRead)
def get_swarm_summary(swarm_run_id: str, db: Session = Depends(get_db)):
    return swarm_query_service.get_swarm_summary(swarm_run_id, db)


@router.get("/{swarm_run_id}/metrics", response_model=SwarmRunMetricsRead)
def get_swarm_metrics(swarm_run_id: str, db: Session = Depends(get_db)):
    return swarm_query_service.get_swarm_metrics(swarm_run_id, db)


@router.get("/{swarm_run_id}/agents", response_model=list[SwarmAgentRunRead])
def list_swarm_agents(
    swarm_run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return swarm_query_service.list_swarm_agents(swarm_run_id, db, limit=limit, offset=offset)


@router.get("/{swarm_run_id}/handoffs", response_model=list[SwarmHandoffRead])
def list_swarm_handoffs(
    swarm_run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return swarm_query_service.list_swarm_handoffs(swarm_run_id, db, limit=limit, offset=offset)


@router.get("/{swarm_run_id}/gate-evaluations", response_model=list[SwarmGateEvaluationRead])
def list_swarm_gate_evaluations(
    swarm_run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return swarm_query_service.list_swarm_gate_evaluations(
        swarm_run_id,
        db,
        limit=limit,
        offset=offset,
    )


@router.get("/{swarm_run_id}/final-output", response_model=SwarmFinalOutputRead)
def get_swarm_final_output(swarm_run_id: str, db: Session = Depends(get_db)):
    return swarm_query_service.get_swarm_final_output(swarm_run_id, db)


@router.get("/{swarm_run_id}", response_model=SwarmRunRead)
def get_swarm_run(swarm_run_id: str, db: Session = Depends(get_db)):
    return swarm_runs_service.get_swarm_run(swarm_run_id, db)


@router.get("", response_model=list[SwarmRunRead])
def list_swarm_runs(
    workflow_id: Optional[str] = Query(default=None),
    status: Optional[SwarmRunStatus] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    return swarm_runs_service.list_swarm_runs(
        db,
        workflow_id=workflow_id,
        status=status,
        limit=limit,
        offset=offset,
        order=order,
    )
