"""Agent Run Metrics ORM models."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AgentRunMetrics(Base, TimestampMixin):
    __tablename__ = "agent_run_metrics"

    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    agent_system: Mapped[str] = mapped_column(String, nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reliability_issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reliability_error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finalization_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_recovery_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    input_tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    schema_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_agent_run_metrics_system_created", "agent_system", "created_at"),
        Index("idx_agent_run_metrics_status_created", "status", "created_at"),
    )
