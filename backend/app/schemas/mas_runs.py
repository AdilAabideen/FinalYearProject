"""Mas Runs schema types."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


MASRunStatus = Literal["created", "running", "completed", "failed", "canceled"]


class MASRunCreateRequest(BaseModel):
    workflow_id: str = Field(description="Stable workflow identifier for the MAS run.")
    workflow_version: Optional[str] = Field(
        default=None,
        description="Optional workflow version used for this mas run.",
    )
    input_schema_name: Optional[str] = Field(
        default=None,
        description="Optional schema name describing the mas input contract.",
    )
    input: dict[str, Any] = Field(description="JSON payload used to start the mas run.")
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional workflow or frontend metadata stored with the mas run.",
    )


class MASRunCreateResponse(BaseModel):
    mas_run_id: str
    status: MASRunStatus


class MASRunUpdateRequest(BaseModel):
    status: Optional[MASRunStatus] = Field(
        default=None,
        description="Optional mas status update.",
    )
    current_agent_run_id: Optional[str] = Field(
        default=None,
        description="Optional currently executing agent run identifier.",
    )
    current_gate_id: Optional[str] = Field(
        default=None,
        description="Optional currently active gate identifier.",
    )
    final_output_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional final output payload to attach to the mas run.",
    )
    error_text: Optional[str] = Field(
        default=None,
        description="Optional error message for failed mas runs.",
    )
    metadata_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional metadata patch for the mas run.",
    )


class MASRunFinalizeRequest(BaseModel):
    status: MASRunStatus = Field(
        description="Terminal mas status applied during finalization.",
    )
    final_output_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional final output payload produced by the mas.",
    )
    error_text: Optional[str] = Field(
        default=None,
        description="Optional terminal error message.",
    )
    current_agent_run_id: Optional[str] = Field(
        default=None,
        description="Optional final agent run responsible for completion.",
    )
    current_gate_id: Optional[str] = Field(
        default=None,
        description="Optional final gate identifier if the mas ended at a gate.",
    )


class MASRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    workflow_version: Optional[str] = None
    status: MASRunStatus
    input_schema_name: Optional[str] = None
    input_json: dict[str, Any]
    metadata_json: Optional[dict[str, Any]] = None
    current_agent_run_id: Optional[str] = None
    current_gate_id: Optional[str] = None
    final_output_json: Optional[dict[str, Any]] = None
    error_text: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime
