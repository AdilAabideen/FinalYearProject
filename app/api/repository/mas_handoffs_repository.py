from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.mas_handoff import MASHandoff


def get_mas_handoff(db: Session, handoff_id: str) -> Optional[MASHandoff]:
    return db.get(MASHandoff, handoff_id)


def save_mas_handoff(db: Session, handoff: MASHandoff, *, refresh: bool = False) -> None:
    db.add(handoff)
    db.commit()
    if refresh:
        db.refresh(handoff)


def list_mas_handoffs_for_run(
    db: Session,
    *,
    mas_run_id: str,
    limit: int = 200,
    offset: int = 0,
) -> list[MASHandoff]:
    stmt = (
        select(MASHandoff)
        .where(MASHandoff.mas_run_id == mas_run_id)
        .order_by(MASHandoff.created_at.asc(), MASHandoff.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def list_pending_handoffs_for_target(
    db: Session,
    *,
    mas_run_id: str,
    to_agent_name: str,
) -> list[MASHandoff]:
    stmt = (
        select(MASHandoff)
        .where(
            MASHandoff.mas_run_id == mas_run_id,
            MASHandoff.to_agent_name == to_agent_name,
            MASHandoff.to_agent_run_id.is_(None),
        )
        .order_by(MASHandoff.created_at.asc(), MASHandoff.id.asc())
    )
    return db.execute(stmt).scalars().all()


def count_mas_handoffs_for_run(db: Session, *, mas_run_id: str) -> int:
    stmt = select(func.count()).select_from(MASHandoff).where(MASHandoff.mas_run_id == mas_run_id)
    return int(db.execute(stmt).scalar_one())
