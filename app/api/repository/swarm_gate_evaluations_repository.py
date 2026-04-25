from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.swarm_gate_evaluation import SwarmGateEvaluation


def get_swarm_gate_evaluation(db: Session, evaluation_id: str) -> Optional[SwarmGateEvaluation]:
    return db.get(SwarmGateEvaluation, evaluation_id)


def save_swarm_gate_evaluation(
    db: Session,
    evaluation: SwarmGateEvaluation,
    *,
    refresh: bool = False,
) -> None:
    db.add(evaluation)
    db.commit()
    if refresh:
        db.refresh(evaluation)


def list_swarm_gate_evaluations_for_run(
    db: Session,
    *,
    swarm_run_id: str,
    limit: int = 200,
    offset: int = 0,
) -> list[SwarmGateEvaluation]:
    stmt = (
        select(SwarmGateEvaluation)
        .where(SwarmGateEvaluation.swarm_run_id == swarm_run_id)
        .order_by(SwarmGateEvaluation.created_at.asc(), SwarmGateEvaluation.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()
