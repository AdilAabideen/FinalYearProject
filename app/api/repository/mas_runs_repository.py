"""Mas Runs Repository repository helpers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mas_run import MASRun


def get_mas_run(db: Session, mas_run_id: str) -> Optional[MASRun]:
    """Return mas run."""
    # Read the current value.
    return db.get(MASRun, mas_run_id)


def save_mas_run(db: Session, mas_run: MASRun, *, refresh: bool = False) -> None:
    """Save mas run."""
    # Keep stored state current.
    db.add(mas_run)
    db.commit()
    if refresh:
        db.refresh(mas_run)


def list_mas_runs(
    db: Session,
    *,
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "desc",
) -> list[MASRun]:
    """List mas runs."""
    # Read the current list.
    stmt = select(MASRun)
    if workflow_id:
        stmt = stmt.where(MASRun.workflow_id == workflow_id)
    if status:
        stmt = stmt.where(MASRun.status == status)

    if order == "asc":
        stmt = stmt.order_by(MASRun.created_at.asc(), MASRun.id.asc())
    else:
        stmt = stmt.order_by(MASRun.created_at.desc(), MASRun.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()
