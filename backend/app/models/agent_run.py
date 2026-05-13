"""Agent Run ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mas_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    workflow_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sequence_index: Mapped[Optional[int]] = mapped_column(nullable=True)
    parent_handoff_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    outgoing_handoff_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_final_agent: Mapped[Optional[bool]] = mapped_column(nullable=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)

    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_agent_runs_mas_run_created_at", "mas_run_id", "created_at"),
        Index("idx_agent_runs_workflow_created_at", "workflow_id", "created_at"),
        Index("idx_agent_runs_agent_name_created_at", "agent_name", "created_at"),
        Index("idx_agent_runs_status_created_at", "status", "created_at"),
    )
