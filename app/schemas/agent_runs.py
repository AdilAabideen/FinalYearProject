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
    input: dict[str, Any] = Field(description="JSON payload passed to the agent.")


class AgentRunCreateResponse(BaseModel):
    run_id: str
    status: RunStatus


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

