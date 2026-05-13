from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.mas_runs import MASRunRead


class MASAgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mas_run_id: Optional[str] = None
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


class MASHandoffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mas_run_id: str
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


class MASGateEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mas_run_id: str
    gate_id: str
    ready: bool
    satisfied_sources_json: list[Any]
    missing_sources_json: list[Any]
    next_target: Optional[str] = None
    handoffs_to_target_json: Optional[list[Any]] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class MASFinalOutputRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mas_run_id: str
    final_agent_run_id: str
    workflow_id: Optional[str] = None
    workflow_version: Optional[str] = None
    output_json: dict[str, Any]
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class MASRunMetricsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mas_run_id: str
    status: str
    duration_ms: Optional[int] = None
    agent_run_count: int
    handoff_count: int
    gate_evaluation_count: int
    completed_agent_count: int
    failed_agent_count: int
    input_tokens_total: int
    output_tokens_total: int
    tokens_total: int
    llm_call_count_total: int
    tool_call_count_total: int
    tool_error_count_total: int
    cost_usd_total: Optional[float] = None
    cost_usd_per_agent_run: Optional[float] = None
    agent_failure_count: int
    reliability_issue_count: int
    reliability_error_count: int
    finalization_failure_count: int
    created_at: datetime
    updated_at: datetime


class MASSummaryCounts(BaseModel):
    agent_run_count: int
    handoff_count: int
    gate_evaluation_count: int
    event_count: int


class MASSummaryRead(BaseModel):
    mas_run: MASRunRead
    current_agent: Optional[MASAgentRunRead] = None
    final_output: Optional[MASFinalOutputRead] = None
    counts: MASSummaryCounts
    metrics: Optional[MASRunMetricsRead] = None
