"""Agent Tool Call ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentToolCall(Base):
    __tablename__ = "agent_tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tool_call_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    result_char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_estimated_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_agent_tool_calls_run_iteration", "run_id", "iteration"),
        Index("idx_agent_tool_calls_run_tool_call", "run_id", "tool_call_id"),
    )
