from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.services import agent_tests_service
from app.database import get_db
from app.schemas.agent_tests import (
    AgentTestCaseCreateRequest,
    AgentTestCaseRead,
    AgentTestCaseUpdateRequest,
    AgentTestRunBatchMetricsRead,
    AgentTestRunDetailRead,
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
    return agent_tests_service.list_cases(
        agent_name=agent_name,
        enabled=enabled,
        limit=limit,
        offset=offset,
        order=order,
        db=db,
    )


@router.post("/cases", response_model=AgentTestCaseRead, status_code=status.HTTP_201_CREATED)
def create_test_case(payload: AgentTestCaseCreateRequest, db: Session = Depends(get_db)):
    return agent_tests_service.create_case(payload, db)


@router.put("/cases/{case_id}", response_model=AgentTestCaseRead)
def update_test_case(case_id: str, payload: AgentTestCaseUpdateRequest, db: Session = Depends(get_db)):
    return agent_tests_service.update_case(case_id, payload, db)


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(case_id: str, db: Session = Depends(get_db)):
    agent_tests_service.delete_case(case_id, db)
    return None


@router.post("/runs/start", response_model=AgentTestRunRead, status_code=status.HTTP_201_CREATED)
def start_test_run(payload: AgentTestRunStartRequest, db: Session = Depends(get_db)):
    return agent_tests_service.start_run(payload, db)


@router.get("/runs", response_model=list[AgentTestRunRead])
def list_test_runs(
    agent_name: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    return agent_tests_service.list_runs(
        agent_name=agent_name,
        limit=limit,
        offset=offset,
        order=order,
        db=db,
    )


@router.get("/runs/{run_id}", response_model=AgentTestRunDetailRead)
def get_test_run(run_id: str, db: Session = Depends(get_db)):
    return agent_tests_service.get_run(run_id, db)


@router.get("/runs/{run_id}/metrics", response_model=AgentTestRunBatchMetricsRead)
def get_test_run_metrics(run_id: str, db: Session = Depends(get_db)):
    return agent_tests_service.get_run_metrics(run_id, db)


@router.get("/runs/{run_id}/stream")
def stream_test_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    return agent_tests_service.stream_run(run_id, db)
