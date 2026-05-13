"""Mas Run Metrics ORM models."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MASRunMetrics(Base, TimestampMixin):
    __tablename__ = "mas_run_metrics"

    mas_run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("mas_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    agent_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    handoff_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gate_evaluation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_agent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_agent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    input_tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_call_count_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_call_count_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_error_count_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_usd_per_agent_run: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    agent_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reliability_issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reliability_error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finalization_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_mas_run_metrics_status_created", "status", "created_at"),
    )
