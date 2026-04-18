from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


RunStatus = Literal["created", "running", "succeeded", "failed", "canceled"]
EventType = Literal[
    "run_start",
    "tool_call",
    "tool_result",
    "thought",
    "assistant",
    "run_end",
    "error",
]


class AgentRunCreateRequest(BaseModel):
    agent_name: str = Field(description="Which agent to run (e.g. 'vitals_agent').")
    model_id: Optional[str] = Field(
        default=None,
        description="Optional model id (e.g. 'gpt-4o-mini', 'medgemma-4b-it').",
    )
    input: dict[str, Any] = Field(description="JSON payload passed to the agent.")


class AgentRunCreateResponse(BaseModel):
    run_id: str
    status: RunStatus


class AgentLLMCallRead(BaseModel):
    id: int
    run_id: str
    call_index: int
    agent_system: str
    agent_name: str
    model_name: Optional[str] = None
    call_kind: str
    iteration: Optional[int] = None
    started_at: datetime
    ended_at: datetime
    latency_ms: int
    input_tokens: int
    output_tokens: int
    tokens_total: int
    usage_source: str
    had_tool_calls: Optional[bool] = None
    tool_call_count: Optional[int] = None
    tool_names: list[str] = Field(default_factory=list)
    cost_usd: Optional[float] = None
    error_text: Optional[str] = None


class AgentToolCallRead(BaseModel):
    id: int
    run_id: str
    agent_name: str
    iteration: int
    tool_call_id: Optional[str] = None
    tool_name: str
    started_at: datetime
    ended_at: datetime
    latency_ms: int
    status: str
    result_char_count: int
    result_estimated_tokens: int
    error_text: Optional[str] = None


class AgentRunMetricsRead(BaseModel):
    run_id: str
    agent_system: str
    agent_name: str
    model_name: Optional[str] = None
    status: RunStatus
    failure_reason: Optional[str] = None
    duration_ms: Optional[int] = None
    llm_call_count: int
    tool_call_count: int
    tool_error_count: int
    reliability_issue_count: int = 0
    reliability_error_count: int = 0
    finalization_failure_count: int = 0
    tool_recovery_failure_count: int = 0
    input_tokens_total: int
    output_tokens_total: int
    tokens_total: int
    cost_usd_total: Optional[float] = None
    schema_valid: Optional[bool] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AgentRunMetricsDetail(BaseModel):
    run_id: str
    metrics: Optional[AgentRunMetricsRead] = None
    llm_calls: list[AgentLLMCallRead]
    tool_calls: list[AgentToolCallRead] = Field(default_factory=list)
    reliability_summary: Optional["AgentRunReliabilitySummary"] = None


class AgentRunMetricsSummary(BaseModel):
    total_runs: int
    successful_runs: int
    success_rate: float
    schema_valid_rate: Optional[float] = None
    tool_error_rate: float
    reliability_failure_rate: float
    finalization_failure_rate: float
    runs_with_reliability_issues: int = 0
    timeout_or_stuck_rate: float
    p50_duration_ms: Optional[float] = None
    p95_duration_ms: Optional[float] = None
    p50_llm_call_count: Optional[float] = None
    p95_llm_call_count: Optional[float] = None
    p50_tokens_total: Optional[float] = None
    p95_tokens_total: Optional[float] = None
    cost_per_successful_run: Optional[float] = None


class AgentRunRead(BaseModel):
    id: str
    agent_name: str
    status: RunStatus
    model_name: Optional[str] = None
    input_json: dict[str, Any]
    output_json: Optional[dict[str, Any]] = None
    error_text: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    metrics: Optional[AgentRunMetricsRead] = None


class AgentRunReliabilityIssueRead(BaseModel):
    id: int
    run_id: str
    agent_name: str
    model_name: Optional[str] = None
    iteration: Optional[int] = None
    call_index: Optional[int] = None
    issue_code: str
    severity: str
    stage: str
    message: str
    details_json: Optional[dict[str, Any]] = None
    assistant_raw_text: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    created_at: datetime


class AgentRunReliabilityIssueCount(BaseModel):
    issue_code: str
    count: int


class AgentRunReliabilitySummary(BaseModel):
    total_issues: int
    error_issues: int
    by_code: list[AgentRunReliabilityIssueCount] = Field(default_factory=list)


class AgentRunReliabilityIssuePage(BaseModel):
    run_id: str
    issues: list[AgentRunReliabilityIssueRead]
    next_offset: int
    total_count: int


class AgentEventRead(BaseModel):
    id: int
    run_id: str
    agent_name: str
    seq: int
    event_type: EventType
    node_name: Optional[str] = None
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    status: Optional[str] = None
    payload_json: Optional[dict[str, Any]] = None
    payload_text: Optional[str] = None
    created_at: datetime


class AgentEventsPage(BaseModel):
    run_id: str
    events: list[AgentEventRead]
    next_after_seq: int


AgentRunMetricsDetail.model_rebuild()
