from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.swarm_final_output import SwarmFinalOutput


def get_swarm_final_output(db: Session, final_output_id: str) -> Optional[SwarmFinalOutput]:
    return db.get(SwarmFinalOutput, final_output_id)


def get_latest_swarm_final_output_for_run(db: Session, *, swarm_run_id: str) -> Optional[SwarmFinalOutput]:
    stmt = (
        select(SwarmFinalOutput)
        .where(SwarmFinalOutput.swarm_run_id == swarm_run_id)
        .order_by(SwarmFinalOutput.created_at.desc(), SwarmFinalOutput.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def save_swarm_final_output(
    db: Session,
    final_output: SwarmFinalOutput,
    *,
    refresh: bool = False,
) -> None:
    db.add(final_output)
    db.commit()
    if refresh:
        db.refresh(final_output)
