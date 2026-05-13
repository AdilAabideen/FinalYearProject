"""Mas Runs Service service helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.repository import mas_runs_repository
from app.api.services import mas_run_metrics_service
from app.models.mas_run import MASRun
from app.schemas.mas_runs import (
    MASRunCreateRequest,
    MASRunCreateResponse,
    MASRunRead,
    MASRunStatus,
)


def _utcnow() -> datetime:
    """Handle the value."""
    # Keep the main step clear.
    return datetime.utcnow()


def _duration_ms(started_at: Optional[datetime], finished_at: Optional[datetime]) -> Optional[int]:
    """Handle ms."""
    # Keep the main step clear.
    if started_at is None or finished_at is None:
        return None
    return max(0, int((finished_at - started_at).total_seconds() * 1000))


def _build_mas_run_read(row: MASRun) -> MASRunRead:
    """Build mas run read."""
    # Build the next value.
    return MASRunRead.model_validate(row, from_attributes=True)


def create_mas_run(payload: MASRunCreateRequest, db: Session) -> MASRunCreateResponse:
    """Create mas run."""
    # Build the new value.
    mas_run_id = str(uuid4())
    now = _utcnow()
    row = MASRun(
        id=mas_run_id,
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
    mas_runs_repository.save_mas_run(db, row)
    return MASRunCreateResponse(mas_run_id=mas_run_id, status="created")


def start_mas_run(mas_run_id: str, db: Session) -> MASRunRead:
    """Start mas run."""
    # Kick off the main step.
    row = mas_runs_repository.get_mas_run(db, mas_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MAS run not found")
    if row.started_at is None:
        row.started_at = _utcnow()
    row.status = "running"
    row.updated_at = _utcnow()
    mas_runs_repository.save_mas_run(db, row)
    return _build_mas_run_read(row)


def update_mas_run(
    mas_run_id: str,
    db: Session,
    *,
    status: Optional[MASRunStatus] = None,
    current_agent_run_id: Optional[str] = None,
    current_gate_id: Optional[str] = None,
    final_output_json: Optional[dict[str, Any]] = None,
    error_text: Optional[str] = None,
    metadata_json: Optional[dict[str, Any]] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
) -> MASRunRead:
    """Update mas run."""
    # Keep stored state current.
    row = mas_runs_repository.get_mas_run(db, mas_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MAS run not found")

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
    mas_runs_repository.save_mas_run(db, row)
    return _build_mas_run_read(row)


def finalize_mas_run(
    mas_run_id: str,
    db: Session,
    *,
    status: MASRunStatus,
    final_output_json: Optional[dict[str, Any]] = None,
    error_text: Optional[str] = None,
    current_agent_run_id: Optional[str] = None,
    current_gate_id: Optional[str] = None,
) -> MASRunRead:
    """Handle mas run."""
    # Keep the main step clear.
    finished_at = _utcnow()
    row = update_mas_run(
        mas_run_id,
        db,
        status=status,
        current_agent_run_id=current_agent_run_id,
        current_gate_id=current_gate_id,
        final_output_json=final_output_json,
        error_text=error_text,
        finished_at=finished_at,
    )
    if status in mas_run_metrics_service.TERMINAL_MAS_STATUSES:
        try:
            mas_run_metrics_service.persist_mas_run_metrics(mas_run_id)
        except Exception:
            pass
    return row


def get_mas_run(mas_run_id: str, db: Session) -> MASRunRead:
    """Return mas run."""
    # Read the current value.
    row = mas_runs_repository.get_mas_run(db, mas_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MAS run not found")
    return _build_mas_run_read(row)


def list_mas_runs(
    db: Session,
    *,
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "desc",
) -> list[MASRunRead]:
    """List mas runs."""
    # Read the current list.
    rows = mas_runs_repository.list_mas_runs(
        db,
        workflow_id=workflow_id,
        status=status,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [_build_mas_run_read(row) for row in rows]
