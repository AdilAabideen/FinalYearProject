from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.repository import (
    agent_runs_repository,
    swarm_events_repository,
    swarm_final_outputs_repository,
    swarm_gate_evaluations_repository,
    swarm_handoffs_repository,
    swarm_run_metrics_repository,
    swarm_runs_repository,
)
from app.api.services import swarm_run_metrics_service
from app.schemas.swarm_read import (
    SwarmAgentRunRead,
    SwarmFinalOutputRead,
    SwarmGateEvaluationRead,
    SwarmHandoffRead,
    SwarmRunMetricsRead,
    SwarmSummaryCounts,
    SwarmSummaryRead,
)
from app.schemas.swarm_runs import SwarmRunRead


def _require_swarm_run(swarm_run_id: str, db: Session):
    row = swarm_runs_repository.get_swarm_run(db, swarm_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swarm run not found")
    return row


def get_swarm_summary(swarm_run_id: str, db: Session) -> SwarmSummaryRead:
    swarm_run = _require_swarm_run(swarm_run_id, db)

    current_agent = None
    if swarm_run.current_agent_run_id:
        current_agent_row = agent_runs_repository.get_run(db, swarm_run.current_agent_run_id)
        if current_agent_row is not None:
            current_agent = SwarmAgentRunRead.model_validate(current_agent_row, from_attributes=True)

    final_output_row = swarm_final_outputs_repository.get_latest_swarm_final_output_for_run(
        db,
        swarm_run_id=swarm_run_id,
    )
    final_output = (
        SwarmFinalOutputRead.model_validate(final_output_row, from_attributes=True)
        if final_output_row is not None
        else None
    )

    counts = SwarmSummaryCounts(
        agent_run_count=agent_runs_repository.count_runs_for_swarm(db, swarm_run_id=swarm_run_id),
        handoff_count=swarm_handoffs_repository.count_swarm_handoffs_for_run(db, swarm_run_id=swarm_run_id),
        gate_evaluation_count=swarm_gate_evaluations_repository.count_swarm_gate_evaluations_for_run(
            db,
            swarm_run_id=swarm_run_id,
        ),
        event_count=swarm_events_repository.count_events_for_swarm(db, swarm_run_id=swarm_run_id),
    )

    metrics_row = swarm_run_metrics_repository.get_swarm_run_metrics(db, swarm_run_id)
    if metrics_row is None and swarm_run.status in swarm_run_metrics_service.TERMINAL_SWARM_STATUSES:
        swarm_run_metrics_service.persist_swarm_run_metrics(swarm_run_id)
        metrics_row = swarm_run_metrics_repository.get_swarm_run_metrics(db, swarm_run_id)

    return SwarmSummaryRead(
        swarm_run=SwarmRunRead.model_validate(swarm_run, from_attributes=True),
        current_agent=current_agent,
        final_output=final_output,
        counts=counts,
        metrics=(
            SwarmRunMetricsRead.model_validate(metrics_row, from_attributes=True)
            if metrics_row is not None
            else None
        ),
    )


def list_swarm_agents(
    swarm_run_id: str,
    db: Session,
    *,
    limit: int = 200,
    offset: int = 0,
) -> list[SwarmAgentRunRead]:
    _require_swarm_run(swarm_run_id, db)
    rows = agent_runs_repository.list_runs_for_swarm(
        db,
        swarm_run_id=swarm_run_id,
        limit=limit,
        offset=offset,
    )
    return [SwarmAgentRunRead.model_validate(row, from_attributes=True) for row in rows]


def list_swarm_handoffs(
    swarm_run_id: str,
    db: Session,
    *,
    limit: int = 200,
    offset: int = 0,
) -> list[SwarmHandoffRead]:
    _require_swarm_run(swarm_run_id, db)
    rows = swarm_handoffs_repository.list_swarm_handoffs_for_run(
        db,
        swarm_run_id=swarm_run_id,
        limit=limit,
        offset=offset,
    )
    return [SwarmHandoffRead.model_validate(row, from_attributes=True) for row in rows]


def list_swarm_gate_evaluations(
    swarm_run_id: str,
    db: Session,
    *,
    limit: int = 200,
    offset: int = 0,
) -> list[SwarmGateEvaluationRead]:
    _require_swarm_run(swarm_run_id, db)
    rows = swarm_gate_evaluations_repository.list_swarm_gate_evaluations_for_run(
        db,
        swarm_run_id=swarm_run_id,
        limit=limit,
        offset=offset,
    )
    return [SwarmGateEvaluationRead.model_validate(row, from_attributes=True) for row in rows]


def get_swarm_final_output(swarm_run_id: str, db: Session) -> SwarmFinalOutputRead:
    _require_swarm_run(swarm_run_id, db)
    row = swarm_final_outputs_repository.get_latest_swarm_final_output_for_run(
        db,
        swarm_run_id=swarm_run_id,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Final output not found")
    return SwarmFinalOutputRead.model_validate(row, from_attributes=True)


def get_swarm_metrics(swarm_run_id: str, db: Session) -> SwarmRunMetricsRead:
    swarm_run = _require_swarm_run(swarm_run_id, db)
    row = swarm_run_metrics_repository.get_swarm_run_metrics(db, swarm_run_id)
    if row is None and swarm_run.status in swarm_run_metrics_service.TERMINAL_SWARM_STATUSES:
        swarm_run_metrics_service.persist_swarm_run_metrics(swarm_run_id)
        row = swarm_run_metrics_repository.get_swarm_run_metrics(db, swarm_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swarm metrics not found")
    return SwarmRunMetricsRead.model_validate(row, from_attributes=True)
