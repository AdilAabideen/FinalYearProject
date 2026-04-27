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
    case_ids: list[str] = Field(description="IDs of the test cases to run, in execution order.")


class MasTestRunRead(BaseModel):
    id: str
    workflow_id: str
    name: Optional[str] = None
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
    swarm_run_id: Optional[str] = None
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
    swarm_run_id: Optional[str] = None
    status: MasTestCaseRunStatus
    passed: Optional[bool] = None
    score: Optional[float] = None
    failure_reason: Optional[str] = None
    swarm_status: Optional[str] = None
    duration_ms: Optional[int] = None


class MasTestRunMetricsSummaryRead(BaseModel):
    total_runs: int
    runs_with_swarm_run: int
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
