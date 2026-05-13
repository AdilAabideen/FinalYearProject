"""Mas Final Outputs Repository repository helpers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mas_final_output import MASFinalOutput


def get_mas_final_output(db: Session, final_output_id: str) -> Optional[MASFinalOutput]:
    """Return mas final output."""
    # Read the current value.
    return db.get(MASFinalOutput, final_output_id)


def get_latest_mas_final_output_for_run(db: Session, *, mas_run_id: str) -> Optional[MASFinalOutput]:
    """Return latest MAS final output for run."""
    # Read the current value.
    stmt = (
        select(MASFinalOutput)
        .where(MASFinalOutput.mas_run_id == mas_run_id)
        .order_by(MASFinalOutput.created_at.desc(), MASFinalOutput.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def save_mas_final_output(
    db: Session,
    final_output: MASFinalOutput,
    *,
    refresh: bool = False,
) -> None:
    """Save mas final output."""
    # Keep stored state current.
    db.add(final_output)
    db.commit()
    if refresh:
        db.refresh(final_output)
