from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mas_test_case import MasTestCase
from app.models.mas_test_case_run import MasTestCaseRun
from app.models.mas_test_run import MasTestRun


def list_test_cases(
    db: Session,
    *,
    workflow_id: Optional[str],
    enabled: Optional[bool],
    limit: int,
    offset: int,
    order: str,
) -> list[MasTestCase]:
    stmt = select(MasTestCase)
    if workflow_id:
        stmt = stmt.where(MasTestCase.workflow_id == workflow_id)
    if enabled is not None:
        stmt = stmt.where(MasTestCase.enabled == enabled)

    if order == "asc":
        stmt = stmt.order_by(MasTestCase.created_at.asc(), MasTestCase.id.asc())
    else:
        stmt = stmt.order_by(MasTestCase.created_at.desc(), MasTestCase.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


def get_test_case(db: Session, case_id: str) -> Optional[MasTestCase]:
    return db.get(MasTestCase, case_id)


def save_test_case(db: Session, case: MasTestCase, *, refresh: bool = False) -> None:
    db.add(case)
    db.commit()
    if refresh:
        db.refresh(case)


def get_test_cases_by_ids(db: Session, case_ids: list[str]) -> list[MasTestCase]:
    stmt = select(MasTestCase).where(MasTestCase.id.in_(case_ids))
    return db.execute(stmt).scalars().all()


def list_test_runs(
    db: Session,
    *,
    workflow_id: Optional[str],
    limit: int,
    offset: int,
    order: str,
) -> list[MasTestRun]:
    stmt = select(MasTestRun)
    if workflow_id:
        stmt = stmt.where(MasTestRun.workflow_id == workflow_id)

    if order == "asc":
        stmt = stmt.order_by(MasTestRun.created_at.asc(), MasTestRun.id.asc())
    else:
        stmt = stmt.order_by(MasTestRun.created_at.desc(), MasTestRun.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


def get_test_run(db: Session, run_id: str) -> Optional[MasTestRun]:
    return db.get(MasTestRun, run_id)


def save_test_run(db: Session, run: MasTestRun, *, refresh: bool = False) -> None:
    db.add(run)
    db.commit()
    if refresh:
        db.refresh(run)


def get_case_runs_for_test_run(db: Session, run_id: str) -> list[MasTestCaseRun]:
    stmt = select(MasTestCaseRun).where(MasTestCaseRun.test_run_id == run_id)
    return db.execute(stmt).scalars().all()


def get_case_runs_by_case_id(db: Session, run_id: str) -> dict[str, MasTestCaseRun]:
    rows = get_case_runs_for_test_run(db, run_id)
    return {row.test_case_id: row for row in rows}


def save_test_case_run(db: Session, case_run: MasTestCaseRun, *, refresh: bool = False) -> None:
    db.add(case_run)
    db.commit()
    if refresh:
        db.refresh(case_run)


def create_test_run_with_case_runs(
    db: Session,
    run: MasTestRun,
    case_runs: list[MasTestCaseRun],
) -> None:
    db.add(run)
    for case_run in case_runs:
        db.add(case_run)
    db.commit()
    db.refresh(run)
