"""Agent Tests Repository repository helpers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.agent_test_case import AgentTestCase
from app.models.agent_test_case_run import AgentTestCaseRun
from app.models.agent_test_run import AgentTestRun


def list_test_cases(
    db: Session,
    *,
    agent_name: Optional[str],
    enabled: Optional[bool],
    limit: int,
    offset: int,
    order: str,
) -> list[AgentTestCase]:
    """List test cases."""
    # Read the current list.
    stmt = select(AgentTestCase)
    if agent_name:
        stmt = stmt.where(AgentTestCase.agent_name == agent_name)
    if enabled is not None:
        stmt = stmt.where(AgentTestCase.enabled == enabled)

    if order == "asc":
        stmt = stmt.order_by(AgentTestCase.created_at.asc(), AgentTestCase.id.asc())
    else:
        stmt = stmt.order_by(AgentTestCase.created_at.desc(), AgentTestCase.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()
def get_test_cases_by_ids(db: Session, case_ids: list[str]) -> list[AgentTestCase]:
    """Return test cases by ids."""
    # Read the current value.
    stmt = select(AgentTestCase).where(AgentTestCase.id.in_(case_ids))
    return db.execute(stmt).scalars().all()


def get_test_run(db: Session, run_id: str) -> Optional[AgentTestRun]:
    """Return test run."""
    # Read the current value.
    return db.get(AgentTestRun, run_id)


def save_test_run(db: Session, run: AgentTestRun, *, refresh: bool = False) -> None:
    """Save test run."""
    # Keep stored state current.
    db.add(run)
    db.commit()
    if refresh:
        db.refresh(run)


def get_case_runs_for_test_run(db: Session, run_id: str) -> list[AgentTestCaseRun]:
    """Return case runs for test run."""
    # Read the current value.
    stmt = select(AgentTestCaseRun).where(AgentTestCaseRun.test_run_id == run_id)
    return db.execute(stmt).scalars().all()


def get_case_runs_by_case_id(db: Session, run_id: str) -> dict[str, AgentTestCaseRun]:
    """Return case runs by case id."""
    # Read the current value.
    rows = get_case_runs_for_test_run(db, run_id)
    return {row.test_case_id: row for row in rows}


def save_test_case_run(db: Session, case_run: AgentTestCaseRun, *, refresh: bool = False) -> None:
    """Save test case run."""
    # Keep stored state current.
    db.add(case_run)
    db.commit()
    if refresh:
        db.refresh(case_run)


def create_test_run_with_case_runs(
    db: Session,
    run: AgentTestRun,
    case_runs: list[AgentTestCaseRun],
) -> None:
    """Create test run with case runs."""
    # Build the new value.
    db.add(run)
    for case_run in case_runs:
        db.add(case_run)
    db.commit()
    db.refresh(run)


def save_agent_run(db: Session, agent_run: AgentRun, *, refresh: bool = False) -> None:
    """Save agent run."""
    # Keep stored state current.
    db.add(agent_run)
    db.commit()
    if refresh:
        db.refresh(agent_run)
