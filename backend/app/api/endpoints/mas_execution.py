"""Mas Execution API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.api.services import mas_execution_service
from app.schemas.mas_execution import MASExecutionStartRequest, MASExecutionStartResponse

router = APIRouter()


@router.post("/{workflow_id}/runs", response_model=MASExecutionStartResponse)
def start_mas_run(
    workflow_id: str,
    payload: MASExecutionStartRequest,
    background_tasks: BackgroundTasks,
):
    """Start mas run."""
    # Kick off the main step.
    return mas_execution_service.start_mas_execution(
        workflow_id=workflow_id,
        payload=payload,
        background_tasks=background_tasks,
    )
