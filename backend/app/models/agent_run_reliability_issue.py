"""Agent Run Reliability Issue ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentRunReliabilityIssue(Base):
    __tablename__ = "agent_run_reliability_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    iteration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    call_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    issue_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String, nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    assistant_raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tool_call_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_agent_rel_issues_run_created", "run_id", "created_at"),
        Index("idx_agent_rel_issues_run_issue_code", "run_id", "issue_code"),
    )
