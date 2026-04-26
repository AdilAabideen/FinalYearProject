from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SwarmRun(Base, TimestampMixin):
    __tablename__ = "swarm_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    workflow_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)

    input_schema_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    current_agent_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_gate_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    final_output_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_swarm_runs_workflow_created_at", "workflow_id", "created_at"),
        Index("idx_swarm_runs_status_created_at", "status", "created_at"),
    )
