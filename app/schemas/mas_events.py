from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class MASEventEnvelope(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mas_run_id: str
    swarm_run_id: Optional[str] = None
    seq: int
    event_type: str
    mas_event_type: Optional[str] = None
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


class MASEventsPage(BaseModel):
    mas_run_id: str
    events: list[MASEventEnvelope]
    next_after_seq: int
