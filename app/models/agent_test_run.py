from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AgentTestRun(Base, TimestampMixin):
    __tablename__ = "agent_test_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)

    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    selected_case_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    metrics_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_agent_test_runs_agent_name_created_at", "agent_name", "created_at"),
    )

