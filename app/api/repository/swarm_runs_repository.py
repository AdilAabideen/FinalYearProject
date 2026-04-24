from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.swarm_run import SwarmRun


def get_swarm_run(db: Session, swarm_run_id: str) -> Optional[SwarmRun]:
    return db.get(SwarmRun, swarm_run_id)


def save_swarm_run(db: Session, swarm_run: SwarmRun, *, refresh: bool = False) -> None:
    db.add(swarm_run)
    db.commit()
    if refresh:
        db.refresh(swarm_run)


def list_swarm_runs(
    db: Session,
    *,
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "desc",
) -> list[SwarmRun]:
    stmt = select(SwarmRun)
    if workflow_id:
        stmt = stmt.where(SwarmRun.workflow_id == workflow_id)
    if status:
        stmt = stmt.where(SwarmRun.status == status)

    if order == "asc":
        stmt = stmt.order_by(SwarmRun.created_at.asc(), SwarmRun.id.asc())
    else:
        stmt = stmt.order_by(SwarmRun.created_at.desc(), SwarmRun.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()
