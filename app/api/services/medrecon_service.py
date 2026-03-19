from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.medrecon import Medrecon
from app.api.repository import medrecon_repository


def get_medrecons(db: Session) -> list[Medrecon]:
    return medrecon_repository.list_all(db)


def get_medrecons_by_subject(
    *,
    subject_id: int,
    charttime_start: Optional[datetime],
    charttime_end: Optional[datetime],
    limit: int,
    offset: int,
    order: str,
    db: Session,
) -> list[Medrecon]:
    if charttime_start and charttime_end and charttime_start > charttime_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="charttime_start must be <= charttime_end",
        )

    return medrecon_repository.list_by_subject(
        db,
        subject_id=subject_id,
        charttime_start=charttime_start,
        charttime_end=charttime_end,
        limit=limit,
        offset=offset,
        order=order,
    )


def get_medrecons_by_subject_with_new_session(
    *,
    subject_id: int,
    charttime_start: Optional[datetime],
    charttime_end: Optional[datetime],
    limit: int,
    offset: int,
    order: str,
) -> list[Medrecon]:
    db = SessionLocal()
    try:
        return get_medrecons_by_subject(
            subject_id=subject_id,
            charttime_start=charttime_start,
            charttime_end=charttime_end,
            limit=limit,
            offset=offset,
            order=order,
            db=db,
        )
    finally:
        db.close()
