from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.swarm_runs import SwarmRunRead


class SwarmAgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    swarm_run_id: Optional[str] = None
    workflow_id: Optional[str] = None
    workflow_version: Optional[str] = None
    sequence_index: Optional[int] = None
    parent_handoff_id: Optional[str] = None
    outgoing_handoff_id: Optional[str] = None
    is_final_agent: Optional[bool] = None
    agent_name: str
    status: str
    model_name: Optional[str] = None
    input_json: dict[str, Any]
    output_json: Optional[dict[str, Any]] = None
    error_text: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SwarmHandoffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    swarm_run_id: str
    from_agent_run_id: str
    from_agent_name: str
    to_agent_name: str
    to_agent_run_id: Optional[str] = None
    handoff_name: str
    payload_schema: Optional[str] = None
    payload_json: dict[str, Any]
    status: str
    accepted_at: Optional[datetime] = None
    latency_ms: Optional[int] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class SwarmGateEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    swarm_run_id: str
    gate_id: str
    ready: bool
    satisfied_sources_json: list[Any]
    missing_sources_json: list[Any]
    next_target: Optional[str] = None
    handoffs_to_target_json: Optional[list[Any]] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class SwarmFinalOutputRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    swarm_run_id: str
    final_agent_run_id: str
    workflow_id: Optional[str] = None
    workflow_version: Optional[str] = None
    output_json: dict[str, Any]
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class SwarmSummaryCounts(BaseModel):
    agent_run_count: int
    handoff_count: int
    gate_evaluation_count: int
    event_count: int


class SwarmSummaryRead(BaseModel):
    swarm_run: SwarmRunRead
    current_agent: Optional[SwarmAgentRunRead] = None
    final_output: Optional[SwarmFinalOutputRead] = None
    counts: SwarmSummaryCounts
