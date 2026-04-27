from __future__ import annotations

from sqlalchemy import JSON, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MasTestCase(Base, TimestampMixin):
    __tablename__ = "mas_test_cases"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    expected_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index("idx_mas_test_cases_workflow_created_at", "workflow_id", "created_at"),
        Index("idx_mas_test_cases_workflow_enabled", "workflow_id", "enabled"),
    )
