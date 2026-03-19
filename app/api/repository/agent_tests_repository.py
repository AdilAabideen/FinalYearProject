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


def get_test_case(db: Session, case_id: str) -> Optional[AgentTestCase]:
    return db.get(AgentTestCase, case_id)


def save_test_case(db: Session, case: AgentTestCase, *, refresh: bool = False) -> None:
    db.add(case)
    db.commit()
    if refresh:
        db.refresh(case)


def get_test_cases_by_ids(db: Session, case_ids: list[str]) -> list[AgentTestCase]:
    stmt = select(AgentTestCase).where(AgentTestCase.id.in_(case_ids))
    return db.execute(stmt).scalars().all()


def list_test_runs(
    db: Session,
    *,
    agent_name: Optional[str],
    limit: int,
    offset: int,
    order: str,
) -> list[AgentTestRun]:
    stmt = select(AgentTestRun)
    if agent_name:
        stmt = stmt.where(AgentTestRun.agent_name == agent_name)

    if order == "asc":
        stmt = stmt.order_by(AgentTestRun.created_at.asc(), AgentTestRun.id.asc())
    else:
        stmt = stmt.order_by(AgentTestRun.created_at.desc(), AgentTestRun.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


def get_test_run(db: Session, run_id: str) -> Optional[AgentTestRun]:
    return db.get(AgentTestRun, run_id)


def save_test_run(db: Session, run: AgentTestRun, *, refresh: bool = False) -> None:
    db.add(run)
    db.commit()
    if refresh:
        db.refresh(run)


def get_case_runs_for_test_run(db: Session, run_id: str) -> list[AgentTestCaseRun]:
    stmt = select(AgentTestCaseRun).where(AgentTestCaseRun.test_run_id == run_id)
    return db.execute(stmt).scalars().all()


def get_case_runs_by_case_id(db: Session, run_id: str) -> dict[str, AgentTestCaseRun]:
    rows = get_case_runs_for_test_run(db, run_id)
    return {row.test_case_id: row for row in rows}


def save_test_case_run(db: Session, case_run: AgentTestCaseRun, *, refresh: bool = False) -> None:
    db.add(case_run)
    db.commit()
    if refresh:
        db.refresh(case_run)


def create_test_run_with_case_runs(
    db: Session,
    run: AgentTestRun,
    case_runs: list[AgentTestCaseRun],
) -> None:
    db.add(run)
    for case_run in case_runs:
        db.add(case_run)
    db.commit()
    db.refresh(run)


def save_agent_run(db: Session, agent_run: AgentRun, *, refresh: bool = False) -> None:
    db.add(agent_run)
    db.commit()
    if refresh:
        db.refresh(agent_run)
