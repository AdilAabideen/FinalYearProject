from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models.medrecon import Medrecon

router = APIRouter()

@router.get('/')
def get_medrecons(db: Session = Depends(get_db)):
    """Get all medrecons """
    stmt = select(Medrecon)
    result = db.execute(stmt)
    medrecons = result.scalars().all()
    return medrecons


@router.get("/subject/{subject_id}")
def get_medrecons_by_subject(
    subject_id: int,
    charttime_start: Optional[datetime] = Query(
        default=None,
        description="Inclusive start charttime (ISO 8601).",
    ),
    charttime_end: Optional[datetime] = Query(
        default=None,
        description="Inclusive end charttime (ISO 8601).",
    ),
    limit: int = Query(default=1000, ge=1, le=10_000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """
    Get medicines (medrecon rows) for a given subject_id with optional charttime filtering.
    """
    if charttime_start and charttime_end and charttime_start > charttime_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="charttime_start must be <= charttime_end",
        )

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
