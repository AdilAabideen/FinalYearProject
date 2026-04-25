from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SwarmGateEvaluation(Base, TimestampMixin):
    __tablename__ = "swarm_gate_evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    swarm_run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    gate_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ready: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    satisfied_sources_json: Mapped[list] = mapped_column(JSON, nullable=False)
    missing_sources_json: Mapped[list] = mapped_column(JSON, nullable=False)
    next_target: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    handoffs_to_target_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_swarm_gate_evals_swarm_created_at", "swarm_run_id", "created_at"),
        Index("idx_swarm_gate_evals_gate_created_at", "gate_id", "created_at"),
        Index("idx_swarm_gate_evals_ready_created_at", "ready", "created_at"),
    )
