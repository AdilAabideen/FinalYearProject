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

