"""Mas Tests Repository repository helpers."""

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
    """List test cases."""
    # Read the current list.
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
def get_test_cases_by_ids(db: Session, case_ids: list[str]) -> list[MasTestCase]:
    """Return test cases by ids."""
    # Read the current value.
    stmt = select(MasTestCase).where(MasTestCase.id.in_(case_ids))
    return db.execute(stmt).scalars().all()


def get_test_run(db: Session, run_id: str) -> Optional[MasTestRun]:
    """Return test run."""
    # Read the current value.
    return db.get(MasTestRun, run_id)


def save_test_run(db: Session, run: MasTestRun, *, refresh: bool = False) -> None:
    """Save test run."""
    # Keep stored state current.
    db.add(run)
    db.commit()
    if refresh:
        db.refresh(run)


def get_case_runs_for_test_run(db: Session, run_id: str) -> list[MasTestCaseRun]:
    """Return case runs for test run."""
    # Read the current value.
    stmt = select(MasTestCaseRun).where(MasTestCaseRun.test_run_id == run_id)
    return db.execute(stmt).scalars().all()


def get_case_runs_by_case_id(db: Session, run_id: str) -> dict[str, MasTestCaseRun]:
    """Return case runs by case id."""
    # Read the current value.
    rows = get_case_runs_for_test_run(db, run_id)
    return {row.test_case_id: row for row in rows}


def save_test_case_run(db: Session, case_run: MasTestCaseRun, *, refresh: bool = False) -> None:
    """Save test case run."""
    # Keep stored state current.
    db.add(case_run)
    db.commit()
    if refresh:
        db.refresh(case_run)


def create_test_run_with_case_runs(
    db: Session,
    run: MasTestRun,
    case_runs: list[MasTestCaseRun],
) -> None:
    """Create test run with case runs."""
    # Build the new value.
    db.add(run)
    for case_run in case_runs:
        db.add(case_run)
    db.commit()
    db.refresh(run)
