"""Mas Gate Evaluations Repository repository helpers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.mas_gate_evaluation import MASGateEvaluation


def get_mas_gate_evaluation(db: Session, evaluation_id: str) -> Optional[MASGateEvaluation]:
    """Return mas gate evaluation."""
    # Read the current value.
    return db.get(MASGateEvaluation, evaluation_id)


def save_mas_gate_evaluation(
    db: Session,
    evaluation: MASGateEvaluation,
    *,
    refresh: bool = False,
) -> None:
    """Save mas gate evaluation."""
    # Keep stored state current.
    db.add(evaluation)
    db.commit()
    if refresh:
        db.refresh(evaluation)


def list_mas_gate_evaluations_for_run(
    db: Session,
    *,
    mas_run_id: str,
    limit: int = 200,
    offset: int = 0,
) -> list[MASGateEvaluation]:
    """List mas gate evaluations for run."""
    # Read the current list.
    stmt = (
        select(MASGateEvaluation)
        .where(MASGateEvaluation.mas_run_id == mas_run_id)
        .order_by(MASGateEvaluation.created_at.asc(), MASGateEvaluation.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def count_mas_gate_evaluations_for_run(db: Session, *, mas_run_id: str) -> int:
    """Count mas gate evaluations for run."""
    # Derive the needed value.
    stmt = (
        select(func.count())
        .select_from(MASGateEvaluation)
        .where(MASGateEvaluation.mas_run_id == mas_run_id)
    )
    return int(db.execute(stmt).scalar_one())
