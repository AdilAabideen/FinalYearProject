from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AgentTestCaseRun(Base, TimestampMixin):
    __tablename__ = "agent_test_case_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    test_run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    test_case_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    agent_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)

    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diff_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metrics_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    error_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("test_run_id", "test_case_id", name="uq_agent_test_case_runs_run_case"),
        Index("idx_agent_test_case_runs_run_created_at", "test_run_id", "created_at"),
    )

