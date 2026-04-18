from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentLLMCall(Base):
    __tablename__ = "agent_llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_index: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_system: Mapped[str] = mapped_column(String, nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    call_kind: Mapped[str] = mapped_column(String, nullable=False, index=True)

    iteration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_source: Mapped[str] = mapped_column(String, nullable=False, default="estimated")
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    had_tool_calls: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    tool_call_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tool_names_json: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    error_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "call_index", name="uq_agent_llm_calls_run_call_index"),
        Index("idx_agent_llm_calls_run_created", "run_id", "started_at"),
        Index("idx_agent_llm_calls_system_created", "agent_system", "started_at"),
    )
