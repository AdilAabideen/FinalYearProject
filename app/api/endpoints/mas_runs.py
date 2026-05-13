from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.services import mas_events_service, mas_query_service, mas_runs_service
from app.database import get_db
from app.schemas.mas_read import (
    MASAgentRunRead,
    MASFinalOutputRead,
    MASGateEvaluationRead,
    MASHandoffRead,
    MASRunMetricsRead,
    MASSummaryRead,
)
from app.schemas.mas_events import MASEventsPage
from app.schemas.mas_runs import (
    MASRunCreateRequest,
    MASRunCreateResponse,
    MASRunFinalizeRequest,
    MASRunRead,
    MASRunStatus,
    MASRunUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=MASRunCreateResponse)
def create_mas_run(payload: MASRunCreateRequest, db: Session = Depends(get_db)):
    return mas_runs_service.create_mas_run(payload, db)


@router.post("/{mas_run_id}/start", response_model=MASRunRead)
def start_mas_run(mas_run_id: str, db: Session = Depends(get_db)):
    return mas_runs_service.start_mas_run(mas_run_id, db)


@router.patch("/{mas_run_id}", response_model=MASRunRead)
def update_mas_run(
    mas_run_id: str,
    payload: MASRunUpdateRequest,
    db: Session = Depends(get_db),
):
    return mas_runs_service.update_mas_run(
        mas_run_id,
        db,
        status=payload.status,
        current_agent_run_id=payload.current_agent_run_id,
        current_gate_id=payload.current_gate_id,
        final_output_json=payload.final_output_json,
        error_text=payload.error_text,
        metadata_json=payload.metadata_json,
    )


@router.post("/{mas_run_id}/finalize", response_model=MASRunRead)
def finalize_mas_run(
    mas_run_id: str,
    payload: MASRunFinalizeRequest,
    db: Session = Depends(get_db),
):
    return mas_runs_service.finalize_mas_run(
        mas_run_id,
        db,
        status=payload.status,
        final_output_json=payload.final_output_json,
        error_text=payload.error_text,
        current_agent_run_id=payload.current_agent_run_id,
        current_gate_id=payload.current_gate_id,
    )


@router.get("/{mas_run_id}/events", response_model=MASEventsPage)
def list_mas_events(
    mas_run_id: str,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return mas_events_service.list_mas_events(mas_run_id, after_seq, limit, db)


@router.get("/{mas_run_id}/events/stream")
def stream_mas_events(
    mas_run_id: str,
    request: Request,
    after_seq: int = Query(default=0, ge=0),
    poll_interval_s: float = Query(default=0.25, ge=0.05, le=5.0),
    db: Session = Depends(get_db),
):
    return mas_events_service.stream_mas_events(mas_run_id, request, after_seq, poll_interval_s, db)


@router.get("/{mas_run_id}/summary", response_model=MASSummaryRead)
def get_mas_summary(mas_run_id: str, db: Session = Depends(get_db)):
    return mas_query_service.get_mas_summary(mas_run_id, db)


@router.get("/{mas_run_id}/metrics", response_model=MASRunMetricsRead)
def get_mas_metrics(mas_run_id: str, db: Session = Depends(get_db)):
    return mas_query_service.get_mas_metrics(mas_run_id, db)


@router.get("/{mas_run_id}/agents", response_model=list[MASAgentRunRead])
def list_mas_agents(
    mas_run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return mas_query_service.list_mas_agents(mas_run_id, db, limit=limit, offset=offset)


@router.get("/{mas_run_id}/handoffs", response_model=list[MASHandoffRead])
def list_mas_handoffs(
    mas_run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return mas_query_service.list_mas_handoffs(mas_run_id, db, limit=limit, offset=offset)


@router.get("/{mas_run_id}/gate-evaluations", response_model=list[MASGateEvaluationRead])
def list_mas_gate_evaluations(
    mas_run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return mas_query_service.list_mas_gate_evaluations(
        mas_run_id,
        db,
        limit=limit,
        offset=offset,
    )


@router.get("/{mas_run_id}/final-output", response_model=MASFinalOutputRead)
def get_mas_final_output(mas_run_id: str, db: Session = Depends(get_db)):
    return mas_query_service.get_mas_final_output(mas_run_id, db)


@router.get("/{mas_run_id}", response_model=MASRunRead)
def get_mas_run(mas_run_id: str, db: Session = Depends(get_db)):
    return mas_runs_service.get_mas_run(mas_run_id, db)


@router.get("", response_model=list[MASRunRead])
def list_mas_runs(
    workflow_id: Optional[str] = Query(default=None),
    status: Optional[MASRunStatus] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    return mas_runs_service.list_mas_runs(
        db,
        workflow_id=workflow_id,
        status=status,
        limit=limit,
        offset=offset,
        order=order,
    )
