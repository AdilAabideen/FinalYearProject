"""Agent Test Case ORM models."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AgentTestCase(Base, TimestampMixin):
    __tablename__ = "agent_test_cases"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    expected_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_agent_test_cases_agent_name_created_at", "agent_name", "created_at"),
        Index("idx_agent_test_cases_agent_name_enabled", "agent_name", "enabled"),
    )
