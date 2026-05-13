"""Mas Handoff ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MASHandoff(Base, TimestampMixin):
    __tablename__ = "mas_handoffs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mas_run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    from_agent_run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    from_agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    to_agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    to_agent_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    handoff_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload_schema: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(nullable=True)

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_mas_handoffs_mas_created_at", "mas_run_id", "created_at"),
        Index("idx_mas_handoffs_from_run_created_at", "from_agent_run_id", "created_at"),
        Index("idx_mas_handoffs_to_agent_created_at", "to_agent_name", "created_at"),
        Index("idx_mas_handoffs_status_created_at", "status", "created_at"),
    )
