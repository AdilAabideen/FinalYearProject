from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.repository import swarm_runs_repository
from app.models.swarm_run import SwarmRun
from app.schemas.swarm_runs import (
    SwarmRunCreateRequest,
    SwarmRunCreateResponse,
    SwarmRunRead,
    SwarmRunStatus,
)


def _utcnow() -> datetime:
    return datetime.utcnow()


def _duration_ms(started_at: Optional[datetime], finished_at: Optional[datetime]) -> Optional[int]:
    if started_at is None or finished_at is None:
        return None
    return max(0, int((finished_at - started_at).total_seconds() * 1000))


def _build_swarm_run_read(row: SwarmRun) -> SwarmRunRead:
    return SwarmRunRead.model_validate(row, from_attributes=True)


def create_swarm_run(payload: SwarmRunCreateRequest, db: Session) -> SwarmRunCreateResponse:
    swarm_run_id = str(uuid4())
    now = _utcnow()
    row = SwarmRun(
        id=swarm_run_id,
        workflow_id=payload.workflow_id,
        workflow_version=payload.workflow_version,
        status="created",
        input_schema_name=payload.input_schema_name,
        input_json=payload.input,
        metadata_json=payload.metadata,
        current_agent_run_id=None,
        current_gate_id=None,
        final_output_json=None,
        error_text=None,
        started_at=None,
        finished_at=None,
        duration_ms=None,
        created_at=now,
        updated_at=now,
    )
    swarm_runs_repository.save_swarm_run(db, row)
    return SwarmRunCreateResponse(swarm_run_id=swarm_run_id, status="created")


def start_swarm_run(swarm_run_id: str, db: Session) -> SwarmRunRead:
    row = swarm_runs_repository.get_swarm_run(db, swarm_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swarm run not found")
    if row.started_at is None:
        row.started_at = _utcnow()
    row.status = "running"
    row.updated_at = _utcnow()
    swarm_runs_repository.save_swarm_run(db, row)
    return _build_swarm_run_read(row)


def update_swarm_run(
    swarm_run_id: str,
    db: Session,
    *,
    status: Optional[SwarmRunStatus] = None,
    current_agent_run_id: Optional[str] = None,
    current_gate_id: Optional[str] = None,
    final_output_json: Optional[dict[str, Any]] = None,
    error_text: Optional[str] = None,
    metadata_json: Optional[dict[str, Any]] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
) -> SwarmRunRead:
    row = swarm_runs_repository.get_swarm_run(db, swarm_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swarm run not found")

    if status is not None:
        row.status = status
    if current_agent_run_id is not None:
        row.current_agent_run_id = current_agent_run_id
    if current_gate_id is not None:
        row.current_gate_id = current_gate_id
    if final_output_json is not None:
        row.final_output_json = final_output_json
    if error_text is not None:
        row.error_text = error_text
    if metadata_json is not None:
        row.metadata_json = metadata_json
    if started_at is not None:
        row.started_at = started_at
    if finished_at is not None:
        row.finished_at = finished_at

    row.duration_ms = _duration_ms(row.started_at, row.finished_at)
    row.updated_at = _utcnow()
    swarm_runs_repository.save_swarm_run(db, row)
    return _build_swarm_run_read(row)


def finalize_swarm_run(
    swarm_run_id: str,
    db: Session,
    *,
    status: SwarmRunStatus,
    final_output_json: Optional[dict[str, Any]] = None,
    error_text: Optional[str] = None,
    current_agent_run_id: Optional[str] = None,
    current_gate_id: Optional[str] = None,
) -> SwarmRunRead:
    finished_at = _utcnow()
    return update_swarm_run(
        swarm_run_id,
        db,
        status=status,
        current_agent_run_id=current_agent_run_id,
        current_gate_id=current_gate_id,
        final_output_json=final_output_json,
        error_text=error_text,
        finished_at=finished_at,
    )


def get_swarm_run(swarm_run_id: str, db: Session) -> SwarmRunRead:
    row = swarm_runs_repository.get_swarm_run(db, swarm_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swarm run not found")
    return _build_swarm_run_read(row)


def list_swarm_runs(
    db: Session,
    *,
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "desc",
) -> list[SwarmRunRead]:
    rows = swarm_runs_repository.list_swarm_runs(
        db,
        workflow_id=workflow_id,
        status=status,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [_build_swarm_run_read(row) for row in rows]
