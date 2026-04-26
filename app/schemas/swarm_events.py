from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


SwarmEventType = Literal[
    "swarm_started",
    "swarm_completed",
    "swarm_failed",
    "agent_started",
    "agent_completed",
    "handoff_created",
    "gate_evaluated",
    "final_output_created",
]


class SwarmEventEnvelope(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    swarm_run_id: str
    seq: int
    event_type: SwarmEventType
    workflow_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    agent_name: Optional[str] = None
    handoff_id: Optional[str] = None
    gate_evaluation_id: Optional[str] = None
    final_output_id: Optional[str] = None
    status: Optional[str] = None
    payload_json: Optional[dict[str, Any]] = None
    payload_text: Optional[str] = None
    created_at: datetime


class SwarmEventsPage(BaseModel):
    swarm_run_id: str
    events: list[SwarmEventEnvelope]
    next_after_seq: int
