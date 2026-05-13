"""Mas Tests API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.services import mas_tests_service
from app.database import get_db
from app.schemas.mas_tests import (
    MasTestCaseRead,
    MasTestRunAnalyticsRead,
    MasTestRunBatchMetricsRead,
    MasTestRunRead,
    MasTestRunStartRequest,
)

router = APIRouter()


@router.get("/cases", response_model=list[MasTestCaseRead])
def list_test_cases(
    workflow_id: Optional[str] = Query(default=None),
    enabled: Optional[bool] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """List test cases."""
    # Read the current list.
    return mas_tests_service.list_cases(
        workflow_id=workflow_id,
        enabled=enabled,
        limit=limit,
        offset=offset,
        order=order,
        db=db,
    )


@router.post("/runs/start", response_model=MasTestRunRead, status_code=status.HTTP_201_CREATED)
def start_test_run(payload: MasTestRunStartRequest, db: Session = Depends(get_db)):
    """Start test run."""
    # Kick off the main step.
    return mas_tests_service.start_run(payload, db)


@router.get("/runs/{run_id}/results", response_model=MasTestRunBatchMetricsRead)
def get_test_run_results(run_id: str, db: Session = Depends(get_db)):
    """Return test run results."""
    # Read the current value.
    return mas_tests_service.get_run_metrics(run_id, db)


@router.get("/runs/{run_id}/metrics", response_model=MasTestRunAnalyticsRead)
def get_test_run_metrics(run_id: str, db: Session = Depends(get_db)):
    """Return test run metrics."""
    # Read the current value.
    return mas_tests_service.get_run_analytics(run_id, db)


@router.get("/runs/{run_id}/stream")
def stream_test_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Stream test run."""
    # Keep events flowing.
    return mas_tests_service.stream_run(run_id, db)
