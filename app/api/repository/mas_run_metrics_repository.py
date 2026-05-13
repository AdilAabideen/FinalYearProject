"""Mas Run Metrics Repository repository helpers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.mas_run_metrics import MASRunMetrics


def get_mas_run_metrics(db: Session, mas_run_id: str) -> Optional[MASRunMetrics]:
    """Return mas run metrics."""
    # Read the current value.
    return db.get(MASRunMetrics, mas_run_id)


def save_mas_run_metrics(
    db: Session,
    metrics: MASRunMetrics,
    *,
    refresh: bool = False,
) -> None:
    """Save mas run metrics."""
    # Keep stored state current.
    db.add(metrics)
    db.commit()
    if refresh:
        db.refresh(metrics)
