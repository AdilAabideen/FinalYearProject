from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.swarm_handoff import SwarmHandoff


def get_swarm_handoff(db: Session, handoff_id: str) -> Optional[SwarmHandoff]:
    return db.get(SwarmHandoff, handoff_id)


def save_swarm_handoff(db: Session, handoff: SwarmHandoff, *, refresh: bool = False) -> None:
    db.add(handoff)
    db.commit()
    if refresh:
        db.refresh(handoff)


def list_swarm_handoffs_for_run(
    db: Session,
    *,
    swarm_run_id: str,
    limit: int = 200,
    offset: int = 0,
) -> list[SwarmHandoff]:
    stmt = (
        select(SwarmHandoff)
        .where(SwarmHandoff.swarm_run_id == swarm_run_id)
        .order_by(SwarmHandoff.created_at.asc(), SwarmHandoff.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()
