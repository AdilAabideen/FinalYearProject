from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.repository import (
    agent_runs_repository,
    mas_events_repository,
    mas_final_outputs_repository,
    mas_gate_evaluations_repository,
    mas_handoffs_repository,
    mas_run_metrics_repository,
    mas_runs_repository,
)
from app.api.services import mas_run_metrics_service
from app.schemas.mas_read import (
    MASAgentRunRead,
    MASFinalOutputRead,
    MASGateEvaluationRead,
    MASHandoffRead,
    MASRunMetricsRead,
    MASSummaryCounts,
    MASSummaryRead,
)
from app.schemas.mas_runs import MASRunRead


def _require_mas_run(mas_run_id: str, db: Session):
    row = mas_runs_repository.get_mas_run(db, mas_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MAS run not found")
    return row


def get_mas_summary(mas_run_id: str, db: Session) -> MASSummaryRead:
    mas_run = _require_mas_run(mas_run_id, db)

    current_agent = None
    if mas_run.current_agent_run_id:
        current_agent_row = agent_runs_repository.get_run(db, mas_run.current_agent_run_id)
        if current_agent_row is not None:
            current_agent = MASAgentRunRead.model_validate(current_agent_row, from_attributes=True)

    final_output_row = mas_final_outputs_repository.get_latest_mas_final_output_for_run(
        db,
        mas_run_id=mas_run_id,
    )
    final_output = (
        MASFinalOutputRead.model_validate(final_output_row, from_attributes=True)
        if final_output_row is not None
        else None
    )

    counts = MASSummaryCounts(
        agent_run_count=agent_runs_repository.count_runs_for_mas(db, mas_run_id=mas_run_id),
        handoff_count=mas_handoffs_repository.count_mas_handoffs_for_run(db, mas_run_id=mas_run_id),
        gate_evaluation_count=mas_gate_evaluations_repository.count_mas_gate_evaluations_for_run(
            db,
            mas_run_id=mas_run_id,
        ),
        event_count=mas_events_repository.count_events_for_mas(db, mas_run_id=mas_run_id),
    )

    metrics_row = mas_run_metrics_repository.get_mas_run_metrics(db, mas_run_id)
    if metrics_row is None and mas_run.status in mas_run_metrics_service.TERMINAL_MAS_STATUSES:
        mas_run_metrics_service.persist_mas_run_metrics(mas_run_id)
        metrics_row = mas_run_metrics_repository.get_mas_run_metrics(db, mas_run_id)

    return MASSummaryRead(
        mas_run=MASRunRead.model_validate(mas_run, from_attributes=True),
        current_agent=current_agent,
        final_output=final_output,
        counts=counts,
        metrics=(
            MASRunMetricsRead.model_validate(metrics_row, from_attributes=True)
            if metrics_row is not None
            else None
        ),
    )


def list_mas_agents(
    mas_run_id: str,
    db: Session,
    *,
    limit: int = 200,
    offset: int = 0,
) -> list[MASAgentRunRead]:
    _require_mas_run(mas_run_id, db)
    rows = agent_runs_repository.list_runs_for_mas(
        db,
        mas_run_id=mas_run_id,
        limit=limit,
        offset=offset,
    )
    return [MASAgentRunRead.model_validate(row, from_attributes=True) for row in rows]


def list_mas_handoffs(
    mas_run_id: str,
    db: Session,
    *,
    limit: int = 200,
    offset: int = 0,
) -> list[MASHandoffRead]:
    _require_mas_run(mas_run_id, db)
    rows = mas_handoffs_repository.list_mas_handoffs_for_run(
        db,
        mas_run_id=mas_run_id,
        limit=limit,
        offset=offset,
    )
    return [MASHandoffRead.model_validate(row, from_attributes=True) for row in rows]


def list_mas_gate_evaluations(
    mas_run_id: str,
    db: Session,
    *,
    limit: int = 200,
    offset: int = 0,
) -> list[MASGateEvaluationRead]:
    _require_mas_run(mas_run_id, db)
    rows = mas_gate_evaluations_repository.list_mas_gate_evaluations_for_run(
        db,
        mas_run_id=mas_run_id,
        limit=limit,
        offset=offset,
    )
    return [MASGateEvaluationRead.model_validate(row, from_attributes=True) for row in rows]


def get_mas_final_output(mas_run_id: str, db: Session) -> MASFinalOutputRead:
    _require_mas_run(mas_run_id, db)
    row = mas_final_outputs_repository.get_latest_mas_final_output_for_run(
        db,
        mas_run_id=mas_run_id,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Final output not found")
    return MASFinalOutputRead.model_validate(row, from_attributes=True)


def get_mas_metrics(mas_run_id: str, db: Session) -> MASRunMetricsRead:
    mas_run = _require_mas_run(mas_run_id, db)
    row = mas_run_metrics_repository.get_mas_run_metrics(db, mas_run_id)
    if row is None and mas_run.status in mas_run_metrics_service.TERMINAL_MAS_STATUSES:
        mas_run_metrics_service.persist_mas_run_metrics(mas_run_id)
        row = mas_run_metrics_repository.get_mas_run_metrics(db, mas_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MAS metrics not found")
    return MASRunMetricsRead.model_validate(row, from_attributes=True)
