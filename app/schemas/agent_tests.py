from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


AgentTestRunStatus = Literal["created", "running", "succeeded", "failed", "canceled"]
AgentTestCaseRunStatus = Literal["created", "running", "succeeded", "failed", "skipped"]


class AgentTestCaseCreateRequest(BaseModel):
    agent_name: str = Field(description="Which agent this test case targets (e.g. 'vitals_agent').")
    name: str
    enabled: bool = True
    input_json: dict[str, Any] = Field(description="Arbitrary agent input payload as JSON.")
    expected_json: dict[str, Any] = Field(description="Expected output subset to match (JSON).")
    notes: Optional[str] = None


class AgentTestCaseUpdateRequest(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    input_json: Optional[dict[str, Any]] = None
    expected_json: Optional[dict[str, Any]] = None
    notes: Optional[str] = None


class AgentTestCaseRead(BaseModel):
    id: str
    agent_name: str
    name: str
    enabled: bool
    input_json: dict[str, Any]
    expected_json: dict[str, Any]
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AgentTestRunStartRequest(BaseModel):
    agent_name: str
    name: Optional[str] = Field(default=None, description="Optional label for UI (e.g. 'demo-1').")
    model_id: Optional[str] = Field(
        default=None,
        description="Optional model id to use for all cases in this run (defaults to server config).",
    )
    case_ids: list[str] = Field(description="IDs of the test cases to run, in execution order.")


class AgentTestRunRead(BaseModel):
    id: str
    agent_name: str
    name: Optional[str] = None
    status: AgentTestRunStatus
    model_name: Optional[str] = None
    selected_case_ids_json: list[str]
    metrics_json: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AgentTestCaseRunRead(BaseModel):
    id: str
    test_run_id: str
    test_case_id: str
    agent_run_id: Optional[str] = None
    status: AgentTestCaseRunStatus
    passed: Optional[bool] = None
    score: Optional[float] = None
    diff_json: Optional[dict[str, Any]] = None
    metrics_json: Optional[dict[str, Any]] = None
    error_text: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AgentTestRunDetailRead(BaseModel):
    run: AgentTestRunRead
    case_runs: list[AgentTestCaseRunRead]


class AgentTestCaseRunMetricRead(BaseModel):
    test_case_id: str
    test_case_name: Optional[str] = None
    agent_run_id: Optional[str] = None
    status: AgentTestCaseRunStatus
    failure_reason: Optional[str] = None
    llm_call_count: Optional[int] = None
    tool_call_count: Optional[int] = None
    tool_error_count: Optional[int] = None
    input_tokens_total: Optional[int] = None
    output_tokens_total: Optional[int] = None
    tokens_total: Optional[int] = None
    duration_ms: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_usd_total: Optional[float] = None


class AgentTestRunMetricsSummaryRead(BaseModel):
    total_runs: int
    runs_with_agent_run: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    missing_metrics_count: int
    llm_call_count_total: int
    tool_call_count_total: int
    tool_error_count_total: int
    input_tokens_total: int
    output_tokens_total: int
    tokens_total: int
    duration_ms_total: int
    cost_usd_total: Optional[float] = None
    llm_call_count_avg: Optional[float] = None
    tool_call_count_avg: Optional[float] = None
    tool_error_count_avg: Optional[float] = None
    input_tokens_avg: Optional[float] = None
    output_tokens_avg: Optional[float] = None
    tokens_avg: Optional[float] = None
    duration_ms_avg: Optional[float] = None
    cost_usd_avg: Optional[float] = None
    cost_usd_avg_successful: Optional[float] = None
    failure_reason_counts: dict[str, int] = Field(default_factory=dict)


class AgentTestRunBatchMetricsRead(BaseModel):
    run: AgentTestRunRead
    summary: AgentTestRunMetricsSummaryRead
    cases: list[AgentTestCaseRunMetricRead]
