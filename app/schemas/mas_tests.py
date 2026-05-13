from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


MasTestRunStatus = Literal["created", "running", "succeeded", "failed", "canceled"]
MasTestCaseRunStatus = Literal["created", "running", "succeeded", "failed", "skipped"]


class MasTestCaseCreateRequest(BaseModel):
    workflow_id: str = Field(description="Which MAS workflow this test case targets.")
    name: str
    enabled: bool = True
    input_json: dict[str, Any] = Field(description="Workflow input payload as JSON.")
    expected_json: dict[str, Any] = Field(description="Expected final output subset to match (JSON).")


class MasTestCaseUpdateRequest(BaseModel):
    workflow_id: Optional[str] = None
    name: Optional[str] = None
    enabled: Optional[bool] = None
    input_json: Optional[dict[str, Any]] = None
    expected_json: Optional[dict[str, Any]] = None


class MasTestCaseRead(BaseModel):
    id: str
    workflow_id: str
    name: str
    enabled: bool
    input_json: dict[str, Any]
    expected_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MasTestRunStartRequest(BaseModel):
    workflow_id: str
    name: Optional[str] = Field(default=None, description="Optional label for UI.")
    model_id: Optional[str] = Field(
        default=None,
        description="Optional model id for this MAS test run (e.g. 'gpt-4o-mini', 'medgemma-4b-it').",
    )
    case_ids: list[str] = Field(description="IDs of the test cases to run, in execution order.")


class MasTestRunRead(BaseModel):
    id: str
    workflow_id: str
    name: Optional[str] = None
    model_name: Optional[str] = None
    status: MasTestRunStatus
    selected_case_ids_json: list[str]
    metrics_json: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MasTestCaseRunRead(BaseModel):
    id: str
    test_run_id: str
    test_case_id: str
    mas_run_id: Optional[str] = None
    status: MasTestCaseRunStatus
    passed: Optional[bool] = None
    score: Optional[float] = None
    diff_json: Optional[dict[str, Any]] = None
    metrics_json: Optional[dict[str, Any]] = None
    error_text: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MasTestRunDetailRead(BaseModel):
    run: MasTestRunRead
    case_runs: list[MasTestCaseRunRead]


class MasTestCaseRunMetricRead(BaseModel):
    test_case_id: str
    test_case_name: Optional[str] = None
    mas_run_id: Optional[str] = None
    status: MasTestCaseRunStatus
    passed: Optional[bool] = None
    score: Optional[float] = None
    failure_reason: Optional[str] = None
    mas_status: Optional[str] = None
    duration_ms: Optional[int] = None


class MasTestRunMetricsSummaryRead(BaseModel):
    total_runs: int
    runs_with_mas_run: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    execution_failed_count: int
    missing_final_output_count: int
    duration_ms_total: int
    duration_ms_avg: Optional[float] = None


class MasTestRunBatchMetricsRead(BaseModel):
    run: MasTestRunRead
    summary: MasTestRunMetricsSummaryRead
    cases: list[MasTestCaseRunMetricRead]


class MasTestCaseAnalyticsRead(BaseModel):
    test_case_id: str
    test_case_name: Optional[str] = None
    mas_run_id: Optional[str] = None
    mas_status: Optional[str] = None
    duration_ms: Optional[int] = None
    agent_run_count: Optional[int] = None
    handoff_count: Optional[int] = None
    gate_evaluation_count: Optional[int] = None
    input_tokens_total: int = 0
    output_tokens_total: int = 0
    tokens_total: int = 0
    llm_call_count_total: int = 0
    tool_call_count_total: int = 0
    tool_error_count_total: int = 0
    cost_usd_total: Optional[float] = None
    cost_usd_per_agent_run: Optional[float] = None
    reliability_issue_count: int = 0
    reliability_error_count: int = 0
    finalization_failure_count: int = 0


class MasTestRunAnalyticsSummaryRead(BaseModel):
    total_cases: int
    cases_with_mas_run: int
    cases_with_metrics: int
    duration_ms_total: int
    duration_ms_avg: Optional[float] = None
    agent_run_count_total: int
    agent_run_count_avg: Optional[float] = None
    handoff_count_total: int
    handoff_count_avg: Optional[float] = None
    gate_evaluation_count_total: int
    gate_evaluation_count_avg: Optional[float] = None
    input_tokens_total: int
    input_tokens_avg: Optional[float] = None
    output_tokens_total: int
    output_tokens_avg: Optional[float] = None
    tokens_total: int
    tokens_avg: Optional[float] = None
    llm_call_count_total: int
    llm_call_count_avg: Optional[float] = None
    tool_call_count_total: int
    tool_call_count_avg: Optional[float] = None
    tool_error_count_total: int
    tool_error_count_avg: Optional[float] = None
    cost_usd_total: Optional[float] = None
    cost_usd_avg: Optional[float] = None
    reliability_issue_count_total: int
    reliability_issue_count_avg: Optional[float] = None
    reliability_error_count_total: int
    reliability_error_count_avg: Optional[float] = None
    finalization_failure_count_total: int
    finalization_failure_count_avg: Optional[float] = None


class MasTestRunAnalyticsRead(BaseModel):
    run: MasTestRunRead
    summary: MasTestRunAnalyticsSummaryRead
    cases: list[MasTestCaseAnalyticsRead]
