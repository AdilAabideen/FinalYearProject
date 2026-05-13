"""Agent Tests API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.services import agent_tests_service
from app.database import get_db
from app.schemas.agent_tests import (
    AgentTestCaseRead,
    AgentTestRunBatchMetricsRead,
    AgentTestRunRead,
    AgentTestRunStartRequest,
)

router = APIRouter()


@router.get("/cases", response_model=list[AgentTestCaseRead])
def list_test_cases(
    agent_name: Optional[str] = Query(default=None),
    enabled: Optional[bool] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """List test cases."""
    # Read the current list.
    return agent_tests_service.list_cases(
        agent_name=agent_name,
        enabled=enabled,
        limit=limit,
        offset=offset,
        order=order,
        db=db,
    )


@router.post("/runs/start", response_model=AgentTestRunRead, status_code=status.HTTP_201_CREATED)
def start_test_run(payload: AgentTestRunStartRequest, db: Session = Depends(get_db)):
    """Start test run."""
    # Kick off the main step.
    return agent_tests_service.start_run(payload, db)


@router.get("/runs/{run_id}/metrics", response_model=AgentTestRunBatchMetricsRead)
def get_test_run_metrics(run_id: str, db: Session = Depends(get_db)):
    """Return test run metrics."""
    # Read the current value.
    return agent_tests_service.get_run_metrics(run_id, db)


@router.get("/runs/{run_id}/stream")
def stream_test_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Stream test run."""
    # Keep events flowing.
    return agent_tests_service.stream_run(run_id, db)
