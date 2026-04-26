from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.api.services import swarm_execution_service
from app.schemas.swarm_execution import SwarmExecutionStartRequest, SwarmExecutionStartResponse

router = APIRouter()


@router.post("/{workflow_id}/runs", response_model=SwarmExecutionStartResponse)
def start_mas_run(
    workflow_id: str,
    payload: SwarmExecutionStartRequest,
    background_tasks: BackgroundTasks,
):
    return swarm_execution_service.start_swarm_execution(
        workflow_id=workflow_id,
        payload=payload,
        background_tasks=background_tasks,
    )
