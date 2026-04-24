from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.services import swarm_runs_service
from app.database import get_db
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
