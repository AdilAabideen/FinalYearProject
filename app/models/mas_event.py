"""Mas Event ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MASEvent(Base):
    __tablename__ = "mas_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mas_run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)

    workflow_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    handoff_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    gate_evaluation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    final_output_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    payload_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("mas_run_id", "seq", name="uq_mas_events_run_seq"),
        Index("idx_mas_events_run_seq", "mas_run_id", "seq"),
        Index("idx_mas_events_type_created_at", "event_type", "created_at"),
    )
