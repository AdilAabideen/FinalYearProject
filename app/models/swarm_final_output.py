from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SwarmFinalOutput(Base, TimestampMixin):
    __tablename__ = "swarm_final_outputs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    swarm_run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    final_agent_run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    workflow_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_swarm_final_outputs_swarm_created_at", "swarm_run_id", "created_at"),
        Index("idx_swarm_final_outputs_agent_created_at", "final_agent_run_id", "created_at"),
    )
