from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medrecon import Medrecon


def list_all(db: Session) -> list[Medrecon]:
    stmt = select(Medrecon)
    result = db.execute(stmt)
    return result.scalars().all()


def list_by_subject(
    db: Session,
    *,
    subject_id: int,
    charttime_start: Optional[datetime],
    charttime_end: Optional[datetime],
    limit: int,
    offset: int,
    order: str,
) -> list[Medrecon]:
    stmt = select(Medrecon).where(Medrecon.subject_id == subject_id)

    if charttime_start:
        stmt = stmt.where(Medrecon.charttime >= charttime_start)
    if charttime_end:
        stmt = stmt.where(Medrecon.charttime <= charttime_end)

    stmt = stmt.order_by(
        Medrecon.charttime.asc() if order == "asc" else Medrecon.charttime.desc()
    )
    stmt = stmt.offset(offset).limit(limit)

    result = db.execute(stmt)
    return result.scalars().all()
