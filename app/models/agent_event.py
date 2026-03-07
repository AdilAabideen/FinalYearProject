from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)

    node_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    payload_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("run_id", "seq", name="uq_agent_events_run_seq"),
        Index("idx_agent_events_run_seq", "run_id", "seq"),
        Index("idx_agent_events_agent_name_created_at", "agent_name", "created_at"),
    )

