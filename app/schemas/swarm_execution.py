from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.swarm_runs import SwarmRunStatus


class SwarmExecutionStartRequest(BaseModel):
    input: dict[str, Any] = Field(
        description="Workflow input payload validated against the MAS input schema.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional caller metadata stored on the swarm run.",
    )


class SwarmExecutionStartResponse(BaseModel):
    swarm_run_id: str
    workflow_id: str
    workflow_version: Optional[str] = None
    input_schema_name: str
    status: SwarmRunStatus
    run_url: str
    summary_url: str
    events_url: str
    events_stream_url: str
    agents_url: str
    handoffs_url: str
    gate_evaluations_url: str
    final_output_url: str
