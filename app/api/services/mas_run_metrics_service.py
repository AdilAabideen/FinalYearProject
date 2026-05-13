from __future__ import annotations

from datetime import datetime

from app.api.repository import (
    agent_metrics_repository,
    agent_runs_repository,
    mas_gate_evaluations_repository,
    mas_handoffs_repository,
    mas_run_metrics_repository,
    mas_runs_repository,
)
from app.database import SessionLocal
from app.models.mas_run_metrics import MASRunMetrics

TERMINAL_MAS_STATUSES = {"completed", "failed", "canceled"}


def persist_mas_run_metrics(mas_run_id: str) -> None:
    db = SessionLocal()
    try:
        mas_run = mas_runs_repository.get_mas_run(db, mas_run_id)
        if mas_run is None:
            return

        agent_runs = agent_runs_repository.list_all_runs_for_mas(db, mas_run_id=mas_run_id)
        agent_run_ids = [run.id for run in agent_runs]
        agent_metric_rows = agent_metrics_repository.list_run_metrics_for_run_ids(db, agent_run_ids)

        cost_values = [row.cost_usd_total for row in agent_metric_rows if row.cost_usd_total is not None]
        cost_usd_total = sum(cost_values) if cost_values else None
        agent_run_count = len(agent_runs)

        metrics = mas_run_metrics_repository.get_mas_run_metrics(db, mas_run_id)
        if metrics is None:
            metrics = MASRunMetrics(
                mas_run_id=mas_run_id,
                status=mas_run.status,
                duration_ms=mas_run.duration_ms,
                agent_run_count=0,
                handoff_count=0,
                gate_evaluation_count=0,
                completed_agent_count=0,
                failed_agent_count=0,
                input_tokens_total=0,
                output_tokens_total=0,
                tokens_total=0,
                llm_call_count_total=0,
                tool_call_count_total=0,
                tool_error_count_total=0,
                cost_usd_total=None,
                cost_usd_per_agent_run=None,
                agent_failure_count=0,
                reliability_issue_count=0,
                reliability_error_count=0,
                finalization_failure_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        metrics.status = mas_run.status
        metrics.duration_ms = mas_run.duration_ms
        metrics.agent_run_count = agent_run_count
        metrics.handoff_count = mas_handoffs_repository.count_mas_handoffs_for_run(
            db,
            mas_run_id=mas_run_id,
        )
        metrics.gate_evaluation_count = mas_gate_evaluations_repository.count_mas_gate_evaluations_for_run(
            db,
            mas_run_id=mas_run_id,
        )
        metrics.completed_agent_count = sum(1 for run in agent_runs if run.status == "succeeded")
        metrics.failed_agent_count = sum(1 for run in agent_runs if run.status == "failed")
        metrics.input_tokens_total = sum(int(row.input_tokens_total or 0) for row in agent_metric_rows)
        metrics.output_tokens_total = sum(int(row.output_tokens_total or 0) for row in agent_metric_rows)
        metrics.tokens_total = sum(int(row.tokens_total or 0) for row in agent_metric_rows)
        metrics.llm_call_count_total = sum(int(row.llm_call_count or 0) for row in agent_metric_rows)
        metrics.tool_call_count_total = sum(int(row.tool_call_count or 0) for row in agent_metric_rows)
        metrics.tool_error_count_total = sum(int(row.tool_error_count or 0) for row in agent_metric_rows)
        metrics.cost_usd_total = cost_usd_total
        metrics.cost_usd_per_agent_run = (
            (cost_usd_total / float(agent_run_count))
            if cost_usd_total is not None and agent_run_count > 0
            else None
        )
        metrics.agent_failure_count = metrics.failed_agent_count
        metrics.reliability_issue_count = sum(int(row.reliability_issue_count or 0) for row in agent_metric_rows)
        metrics.reliability_error_count = sum(int(row.reliability_error_count or 0) for row in agent_metric_rows)
        metrics.finalization_failure_count = sum(
            int(row.finalization_failure_count or 0)
            for row in agent_metric_rows
        )
        metrics.updated_at = datetime.utcnow()
        mas_run_metrics_repository.save_mas_run_metrics(db, metrics)
    finally:
        db.close()
