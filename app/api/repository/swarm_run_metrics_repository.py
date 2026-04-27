from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.swarm_run_metrics import SwarmRunMetrics


def get_swarm_run_metrics(db: Session, swarm_run_id: str) -> Optional[SwarmRunMetrics]:
    return db.get(SwarmRunMetrics, swarm_run_id)


def save_swarm_run_metrics(
    db: Session,
    metrics: SwarmRunMetrics,
    *,
    refresh: bool = False,
) -> None:
    db.add(metrics)
    db.commit()
    if refresh:
        db.refresh(metrics)
