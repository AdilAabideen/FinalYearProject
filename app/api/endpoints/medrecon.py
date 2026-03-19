from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.services import medrecon_service
from app.database import get_db

router = APIRouter()


@router.get("/")
def get_medrecons(db: Session = Depends(get_db)):
    return medrecon_service.get_medrecons(db)


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
    return medrecon_service.get_medrecons_by_subject(
        subject_id=subject_id,
        charttime_start=charttime_start,
        charttime_end=charttime_end,
        limit=limit,
        offset=offset,
        order=order,
        db=db,
    )
