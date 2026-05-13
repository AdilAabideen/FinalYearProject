"""Mas Execution schema types."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.mas_runs import MASRunStatus


class MASExecutionStartRequest(BaseModel):
    input: dict[str, Any] = Field(
        description="Workflow input payload validated against the MAS input schema.",
    )
    model_id: Optional[str] = Field(
        default=None,
        description="Optional model id for this MAS run (e.g. 'gpt-4o-mini', 'medgemma-4b-it').",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional caller metadata stored on the mas run.",
    )


class MASExecutionStartResponse(BaseModel):
    mas_run_id: str
    swarm_run_id: Optional[str] = None
    workflow_id: str
    workflow_version: Optional[str] = None
    input_schema_name: str
    model_id: str
    status: MASRunStatus
    run_url: str
    summary_url: str
    events_url: str
    events_stream_url: str
    agents_url: str
    handoffs_url: str
    gate_evaluations_url: str
    final_output_url: str
