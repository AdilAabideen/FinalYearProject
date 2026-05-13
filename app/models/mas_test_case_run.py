from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.mas_test_case import MasTestCase
    from app.models.mas_test_run import MasTestRun
    from app.models.mas_run import MASRun


class MasTestCaseRun(Base, TimestampMixin):
    __tablename__ = "mas_test_case_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    test_run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("mas_test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("mas_test_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    mas_run_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("mas_runs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)

    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diff_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metrics_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    test_run: Mapped["MasTestRun"] = relationship("MasTestRun")
    test_case: Mapped["MasTestCase"] = relationship("MasTestCase")
    mas_run: Mapped[Optional["MASRun"]] = relationship("MASRun")

    __table_args__ = (
        UniqueConstraint("test_run_id", "test_case_id", name="uq_mas_test_case_runs_run_case"),
        Index("idx_mas_test_case_runs_run_created_at", "test_run_id", "created_at"),
    )
