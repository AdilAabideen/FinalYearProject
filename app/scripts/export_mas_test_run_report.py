"""Export Mas Test Run Report script helpers."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select

from app.database import SessionLocal, ensure_runtime_schema_upgrades
from app.models.agent_event import AgentEvent
from app.models.agent_llm_call import AgentLLMCall
from app.models.agent_run import AgentRun
from app.models.mas_test_case import MasTestCase
from app.models.mas_test_case_run import MasTestCaseRun
from app.models.mas_test_run import MasTestRun
from app.models.mas_event import MASEvent
from app.models.mas_final_output import MASFinalOutput
from app.models.mas_handoff import MASHandoff
from app.models.mas_run import MASRun
from app.models.mas_run_metrics import MASRunMetrics


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "reports" / "mas_test_runs"
PREVIEW_LEN = 500


@dataclass
class ExportBundle:
    report_kind: str
    report_id: str
    mas_test_run: MasTestRun | None
    case_runs: list[MasTestCaseRun]
    test_cases: dict[str, MasTestCase]
    mas_runs: dict[str, MASRun]
    mas_metrics: dict[str, MASRunMetrics]
    mas_events: list[MASEvent]
    mas_handoffs: list[MASHandoff]
    mas_final_outputs: list[MASFinalOutput]
    agent_runs: list[AgentRun]
    agent_events: list[AgentEvent]
    agent_llm_calls: list[AgentLLMCall]


def _model_name_for_bundle(bundle: ExportBundle) -> str:
    """Handle name for bundle."""
    # Keep the main step clear.
    if bundle.mas_test_run and bundle.mas_test_run.model_name:
        return bundle.mas_test_run.model_name
    model_names = sorted({row.model_name for row in bundle.agent_runs if row.model_name})
    if not model_names:
        return ""
    if len(model_names) == 1:
        return model_names[0]
    return ", ".join(model_names)


def _json_dumps(value: Any) -> str:
    """Handle dumps."""
    # Keep the main step clear.
    return json.dumps(value, ensure_ascii=False, default=str)


def _preview(value: Any, limit: int = PREVIEW_LEN) -> str:
    """Handle the value."""
    # Keep the main step clear.
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = _json_dumps(value)
    text = text.replace("\r", " ").replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "...(truncated)"


def _dt(value: Any) -> str:
    """Handle the value."""
    # Keep the main step clear.
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _duration_s(started_at: datetime | None, finished_at: datetime | None) -> str:
    """Handle s."""
    # Keep the main step clear.
    if started_at is None or finished_at is None:
        return ""
    return f"{(finished_at - started_at).total_seconds():.3f}"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    """Handle csv."""
    # Keep the main step clear.
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _safe_json(value: Any) -> Any:
    """Handle json."""
    # Keep the main step clear.
    if isinstance(value, (dict, list)):
        return value
    return value


def _classify_agent_failure(agent_run: AgentRun) -> str:
    """Handle agent failure."""
    # Keep the main step clear.
    output = dict(agent_run.output_json or {})
    raw_result = dict(output.get("raw_result") or {})
    raw_output = raw_result.get("raw_output") or ""
    reason = str(raw_result.get("reason") or output.get("reason") or "").strip()
    error = str(raw_result.get("error") or output.get("error") or agent_run.error_text or "").strip()

    if "handoff_tool_result_unparseable" in reason:
        return "handoff_payload_invalid"
    if '"name": "handoff"' in raw_output:
        return "generic_handoff_tool"
    if "esi2_or_rule" in raw_output or "esi2_final_action_rule" in raw_output:
        return "wrong_terminal_tool"
    if '{"final_answer":' in raw_output or '"final_answer": {' in raw_output:
        return "plain_final_answer_json"
    if '"tool_name"' in raw_output:
        return "tool_name_transport_shape"
    if '"tool_calls"' in raw_output and '"status": "success"' in raw_output:
        return "tool_result_transcript_imitation"
    if raw_output.count("THINKING") > 3:
        return "runaway_thinking_loop"
    if raw_output and not raw_output.rstrip().endswith(("}", "]", "```")):
        return "truncated_output"
    if reason:
        return reason
    if error:
        return error
    return "unknown_failure"


def _collect_bundle(mas_test_run_id: str) -> ExportBundle:
    """Handle bundle."""
    # Keep the main step clear.
    ensure_runtime_schema_upgrades()
    db = SessionLocal()
    try:
        mas_test_run = db.scalar(select(MasTestRun).where(MasTestRun.id == mas_test_run_id))
        if mas_test_run is None:
            raise ValueError(f"MAS test run not found: {mas_test_run_id}")

        case_runs = list(
            db.scalars(
                select(MasTestCaseRun)
                .where(MasTestCaseRun.test_run_id == mas_test_run_id)
                .order_by(MasTestCaseRun.started_at, MasTestCaseRun.created_at, MasTestCaseRun.id)
            )
        )
        test_case_ids = [row.test_case_id for row in case_runs]
        test_cases = {
            row.id: row
            for row in db.scalars(select(MasTestCase).where(MasTestCase.id.in_(test_case_ids)))
        } if test_case_ids else {}

        mas_run_ids = [row.mas_run_id for row in case_runs if row.mas_run_id]
        mas_runs = {
            row.id: row
            for row in db.scalars(select(MASRun).where(MASRun.id.in_(mas_run_ids)))
        } if mas_run_ids else {}
        mas_metrics = {
            row.mas_run_id: row
            for row in db.scalars(select(MASRunMetrics).where(MASRunMetrics.mas_run_id.in_(mas_run_ids)))
        } if mas_run_ids else {}
        mas_events = list(
            db.scalars(
                select(MASEvent)
                .where(MASEvent.mas_run_id.in_(mas_run_ids))
                .order_by(MASEvent.mas_run_id, MASEvent.seq)
            )
        ) if mas_run_ids else []
        mas_handoffs = list(
            db.scalars(
                select(MASHandoff)
                .where(MASHandoff.mas_run_id.in_(mas_run_ids))
                .order_by(MASHandoff.mas_run_id, MASHandoff.created_at, MASHandoff.id)
            )
        ) if mas_run_ids else []
        mas_final_outputs = list(
            db.scalars(
                select(MASFinalOutput)
                .where(MASFinalOutput.mas_run_id.in_(mas_run_ids))
                .order_by(MASFinalOutput.mas_run_id, MASFinalOutput.created_at, MASFinalOutput.id)
            )
        ) if mas_run_ids else []

        agent_runs = list(
            db.scalars(
                select(AgentRun)
                .where(AgentRun.mas_run_id.in_(mas_run_ids))
                .order_by(AgentRun.mas_run_id, AgentRun.sequence_index, AgentRun.started_at, AgentRun.created_at)
            )
        ) if mas_run_ids else []
        agent_run_ids = [row.id for row in agent_runs]

        agent_events = list(
            db.scalars(
                select(AgentEvent)
                .where(AgentEvent.run_id.in_(agent_run_ids))
                .order_by(AgentEvent.run_id, AgentEvent.seq)
            )
        ) if agent_run_ids else []
        agent_llm_calls = list(
            db.scalars(
                select(AgentLLMCall)
                .where(AgentLLMCall.run_id.in_(agent_run_ids))
                .order_by(AgentLLMCall.run_id, AgentLLMCall.call_index)
            )
        ) if agent_run_ids else []

        return ExportBundle(
            report_kind="mas_test_run",
            report_id=mas_test_run.id,
            mas_test_run=mas_test_run,
            case_runs=case_runs,
            test_cases=test_cases,
            mas_runs=mas_runs,
            mas_metrics=mas_metrics,
            mas_events=mas_events,
            mas_handoffs=mas_handoffs,
            mas_final_outputs=mas_final_outputs,
            agent_runs=agent_runs,
            agent_events=agent_events,
            agent_llm_calls=agent_llm_calls,
        )
    finally:
        db.close()


def _collect_bundle_for_mas_runs(
    mas_run_ids: list[str],
    *,
    label: str | None = None,
) -> ExportBundle:
    """Handle bundle for MAS runs."""
    # Keep the main step clear.
    ensure_runtime_schema_upgrades()
    normalized_ids = [str(run_id).strip() for run_id in mas_run_ids if str(run_id).strip()]
    if not normalized_ids:
        raise ValueError("At least one mas run id is required.")

    db = SessionLocal()
    try:
        mas_runs_list = list(
            db.scalars(
                select(MASRun)
                .where(MASRun.id.in_(normalized_ids))
                .order_by(MASRun.created_at, MASRun.id)
            )
        )
        found_ids = {row.id for row in mas_runs_list}
        missing = [run_id for run_id in normalized_ids if run_id not in found_ids]
        if missing:
            raise ValueError(f"MAS run(s) not found: {', '.join(missing)}")

        case_runs = list(
            db.scalars(
                select(MasTestCaseRun)
                .where(MasTestCaseRun.mas_run_id.in_(normalized_ids))
                .order_by(MasTestCaseRun.started_at, MasTestCaseRun.created_at, MasTestCaseRun.id)
            )
        )
        test_case_ids = [row.test_case_id for row in case_runs]
        test_cases = {
            row.id: row
            for row in db.scalars(select(MasTestCase).where(MasTestCase.id.in_(test_case_ids)))
        } if test_case_ids else {}

        mas_runs = {row.id: row for row in mas_runs_list}
        mas_metrics = {
            row.mas_run_id: row
            for row in db.scalars(select(MASRunMetrics).where(MASRunMetrics.mas_run_id.in_(normalized_ids)))
        }
        mas_events = list(
            db.scalars(
                select(MASEvent)
                .where(MASEvent.mas_run_id.in_(normalized_ids))
                .order_by(MASEvent.mas_run_id, MASEvent.seq)
            )
        )
        mas_handoffs = list(
            db.scalars(
                select(MASHandoff)
                .where(MASHandoff.mas_run_id.in_(normalized_ids))
                .order_by(MASHandoff.mas_run_id, MASHandoff.created_at, MASHandoff.id)
            )
        )
        mas_final_outputs = list(
            db.scalars(
                select(MASFinalOutput)
                .where(MASFinalOutput.mas_run_id.in_(normalized_ids))
                .order_by(MASFinalOutput.mas_run_id, MASFinalOutput.created_at, MASFinalOutput.id)
            )
        )

        agent_runs = list(
            db.scalars(
                select(AgentRun)
                .where(AgentRun.mas_run_id.in_(normalized_ids))
                .order_by(AgentRun.mas_run_id, AgentRun.sequence_index, AgentRun.started_at, AgentRun.created_at)
            )
        )
        agent_run_ids = [row.id for row in agent_runs]
        agent_events = list(
            db.scalars(
                select(AgentEvent)
                .where(AgentEvent.run_id.in_(agent_run_ids))
                .order_by(AgentEvent.run_id, AgentEvent.seq)
            )
        ) if agent_run_ids else []
        agent_llm_calls = list(
            db.scalars(
                select(AgentLLMCall)
                .where(AgentLLMCall.run_id.in_(agent_run_ids))
                .order_by(AgentLLMCall.run_id, AgentLLMCall.call_index)
            )
        ) if agent_run_ids else []

        report_id = label.strip() if isinstance(label, str) and label.strip() else f"mas_group_{uuid4().hex[:8]}"
        return ExportBundle(
            report_kind="mas_run_group",
            report_id=report_id,
            mas_test_run=None,
            case_runs=case_runs,
            test_cases=test_cases,
            mas_runs=mas_runs,
            mas_metrics=mas_metrics,
            mas_events=mas_events,
            mas_handoffs=mas_handoffs,
            mas_final_outputs=mas_final_outputs,
            agent_runs=agent_runs,
            agent_events=agent_events,
            agent_llm_calls=agent_llm_calls,
        )
    finally:
        db.close()


def _build_mas_test_run_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build mas test run rows."""
    # Build the next value.
    run = bundle.mas_test_run
    succeeded = sum(1 for row in bundle.case_runs if row.status == "succeeded")
    failed = sum(1 for row in bundle.case_runs if row.status == "failed")
    total = len(bundle.case_runs)
    success_rate = (succeeded / total) if total else 0.0
    return [
        {
            "report_kind": bundle.report_kind,
            "report_id": bundle.report_id,
            "mas_test_run_id": run.id if run else "",
            "workflow_id": run.workflow_id if run else "",
            "model_name": _model_name_for_bundle(bundle),
            "name": (run.name or "") if run else "",
            "status": run.status if run else "",
            "selected_case_count": len(run.selected_case_ids_json or []) if run else len(bundle.mas_runs),
            "case_run_count": total,
            "succeeded_case_runs": succeeded,
            "failed_case_runs": failed,
            "success_rate": f"{success_rate:.3f}",
            "started_at": _dt(run.started_at) if run else "",
            "finished_at": _dt(run.finished_at) if run else "",
            "duration_s": _duration_s(run.started_at, run.finished_at) if run else "",
            "metrics_json": _json_dumps(_safe_json(run.metrics_json)) if run and run.metrics_json is not None else "",
        }
    ]


def _build_case_run_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build case run rows."""
    # Build the next value.
    rows: list[dict[str, Any]] = []
    for row in bundle.case_runs:
        test_case = bundle.test_cases.get(row.test_case_id)
        rows.append(
            {
                "mas_test_case_run_id": row.id,
                "mas_test_run_id": row.test_run_id,
                "report_id": bundle.report_id,
                "test_case_id": row.test_case_id,
                "test_case_name": test_case.name if test_case else "",
                "mas_run_id": row.mas_run_id or "",
                "status": row.status,
                "passed": row.passed,
                "score": row.score,
                "error_text": row.error_text or "",
                "started_at": _dt(row.started_at),
                "finished_at": _dt(row.finished_at),
                "duration_s": _duration_s(row.started_at, row.finished_at),
                "metrics_json": _json_dumps(_safe_json(row.metrics_json)) if row.metrics_json is not None else "",
                "diff_json": _json_dumps(_safe_json(row.diff_json)) if row.diff_json is not None else "",
                "case_input_json": _json_dumps(_safe_json(test_case.input_json)) if test_case else "",
                "expected_json": _json_dumps(_safe_json(test_case.expected_json)) if test_case else "",
            }
        )
    return rows


def _build_mas_run_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build mas run rows."""
    # Build the next value.
    agent_runs_by_mas: dict[str, list[AgentRun]] = defaultdict(list)
    for row in bundle.agent_runs:
        if row.mas_run_id:
            agent_runs_by_mas[row.mas_run_id].append(row)
    handoff_count_by_mas = Counter(row.mas_run_id for row in bundle.mas_handoffs)
    event_count_by_mas = Counter(row.mas_run_id for row in bundle.mas_events)
    final_output_ids = {row.mas_run_id for row in bundle.mas_final_outputs}
    case_run_by_mas = {row.mas_run_id: row for row in bundle.case_runs if row.mas_run_id}

    rows: list[dict[str, Any]] = []
    for mas_run_id, mas_run in bundle.mas_runs.items():
        metric = bundle.mas_metrics.get(mas_run_id)
        agent_runs = agent_runs_by_mas.get(mas_run_id, [])
        case_run = case_run_by_mas.get(mas_run_id)
        rows.append(
            {
                "mas_run_id": mas_run.id,
                "mas_test_run_id": bundle.mas_test_run.id if bundle.mas_test_run else "",
                "report_id": bundle.report_id,
                "mas_test_case_run_id": case_run.id if case_run else "",
                "test_case_id": case_run.test_case_id if case_run else "",
                "workflow_id": mas_run.workflow_id,
                "workflow_version": mas_run.workflow_version or "",
                "status": mas_run.status,
                "error_text": mas_run.error_text or "",
                "started_at": _dt(mas_run.started_at),
                "finished_at": _dt(mas_run.finished_at),
                "duration_ms": mas_run.duration_ms if mas_run.duration_ms is not None else "",
                "duration_s": _duration_s(mas_run.started_at, mas_run.finished_at),
                "num_agent_runs": len(agent_runs),
                "num_failed_agent_runs": sum(1 for row in agent_runs if row.status == "failed"),
                "num_handoffs": handoff_count_by_mas.get(mas_run_id, 0),
                "num_mas_events": event_count_by_mas.get(mas_run_id, 0),
                "has_final_output": mas_run_id in final_output_ids,
                "input_json": _json_dumps(_safe_json(mas_run.input_json)),
                "metadata_json": _json_dumps(_safe_json(mas_run.metadata_json)) if mas_run.metadata_json is not None else "",
                "final_output_json": _json_dumps(_safe_json(mas_run.final_output_json)) if mas_run.final_output_json is not None else "",
                "metrics_status": metric.status if metric else "",
                "metrics_tokens_total": metric.tokens_total if metric else "",
                "metrics_llm_call_count_total": metric.llm_call_count_total if metric else "",
            }
        )
    return rows


def _build_mas_metric_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build mas metric rows."""
    # Build the next value.
    rows: list[dict[str, Any]] = []
    for metric in bundle.mas_metrics.values():
        rows.append(
            {
                "mas_run_id": metric.mas_run_id,
                "status": metric.status,
                "duration_ms": metric.duration_ms if metric.duration_ms is not None else "",
                "agent_run_count": metric.agent_run_count,
                "handoff_count": metric.handoff_count,
                "gate_evaluation_count": metric.gate_evaluation_count,
                "completed_agent_count": metric.completed_agent_count,
                "failed_agent_count": metric.failed_agent_count,
                "input_tokens_total": metric.input_tokens_total,
                "output_tokens_total": metric.output_tokens_total,
                "tokens_total": metric.tokens_total,
                "llm_call_count_total": metric.llm_call_count_total,
                "tool_call_count_total": metric.tool_call_count_total,
                "tool_error_count_total": metric.tool_error_count_total,
                "cost_usd_total": metric.cost_usd_total if metric.cost_usd_total is not None else "",
                "cost_usd_per_agent_run": metric.cost_usd_per_agent_run if metric.cost_usd_per_agent_run is not None else "",
                "agent_failure_count": metric.agent_failure_count,
                "reliability_issue_count": metric.reliability_issue_count,
                "reliability_error_count": metric.reliability_error_count,
                "finalization_failure_count": metric.finalization_failure_count,
                "created_at": _dt(metric.created_at),
                "updated_at": _dt(metric.updated_at),
            }
        )
    return rows


def _build_mas_event_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build mas event rows."""
    # Build the next value.
    return [
        {
            "mas_run_id": row.mas_run_id,
            "seq": row.seq,
            "event_type": row.event_type,
            "workflow_id": row.workflow_id or "",
            "agent_run_id": row.agent_run_id or "",
            "agent_name": row.agent_name or "",
            "handoff_id": row.handoff_id or "",
            "gate_evaluation_id": row.gate_evaluation_id or "",
            "final_output_id": row.final_output_id or "",
            "status": row.status or "",
            "payload_preview": _preview(row.payload_text or row.payload_json),
            "payload_json": _json_dumps(_safe_json(row.payload_json)) if row.payload_json is not None else "",
            "payload_text": row.payload_text or "",
            "created_at": _dt(row.created_at),
        }
        for row in bundle.mas_events
    ]


def _build_handoff_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build handoff rows."""
    # Build the next value.
    return [
        {
            "handoff_id": row.id,
            "mas_run_id": row.mas_run_id,
            "from_agent_run_id": row.from_agent_run_id,
            "from_agent_name": row.from_agent_name,
            "to_agent_name": row.to_agent_name,
            "to_agent_run_id": row.to_agent_run_id or "",
            "handoff_name": row.handoff_name,
            "payload_schema": row.payload_schema or "",
            "payload_preview": _preview(row.payload_json),
            "payload_json": _json_dumps(_safe_json(row.payload_json)),
            "status": row.status,
            "accepted_at": _dt(row.accepted_at),
            "latency_ms": row.latency_ms if row.latency_ms is not None else "",
            "metadata_json": _json_dumps(_safe_json(row.metadata_json)) if row.metadata_json is not None else "",
            "created_at": _dt(row.created_at),
            "updated_at": _dt(row.updated_at),
        }
        for row in bundle.mas_handoffs
    ]


def _build_final_output_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build final output rows."""
    # Build the next value.
    return [
        {
            "final_output_id": row.id,
            "mas_run_id": row.mas_run_id,
            "final_agent_run_id": row.final_agent_run_id,
            "workflow_id": row.workflow_id or "",
            "workflow_version": row.workflow_version or "",
            "output_preview": _preview(row.output_json),
            "output_json": _json_dumps(_safe_json(row.output_json)),
            "metadata_json": _json_dumps(_safe_json(row.metadata_json)) if row.metadata_json is not None else "",
            "created_at": _dt(row.created_at),
            "updated_at": _dt(row.updated_at),
        }
        for row in bundle.mas_final_outputs
    ]


def _build_agent_run_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build agent run rows."""
    # Build the next value.
    events_by_run: dict[str, list[AgentEvent]] = defaultdict(list)
    for row in bundle.agent_events:
        events_by_run[row.run_id].append(row)
    llm_by_run: dict[str, list[AgentLLMCall]] = defaultdict(list)
    for row in bundle.agent_llm_calls:
        llm_by_run[row.run_id].append(row)

    rows: list[dict[str, Any]] = []
    for row in bundle.agent_runs:
        events = events_by_run.get(row.id, [])
        llm_calls = llm_by_run.get(row.id, [])
        rows.append(
            {
                "agent_run_id": row.id,
                "mas_run_id": row.mas_run_id or "",
                "mas_test_run_id": bundle.mas_test_run.id if bundle.mas_test_run else "",
                "report_id": bundle.report_id,
                "workflow_id": row.workflow_id or "",
                "workflow_version": row.workflow_version or "",
                "sequence_index": row.sequence_index if row.sequence_index is not None else "",
                "parent_handoff_id": row.parent_handoff_id or "",
                "outgoing_handoff_id": row.outgoing_handoff_id or "",
                "is_final_agent": row.is_final_agent,
                "agent_name": row.agent_name,
                "status": row.status,
                "model_name": row.model_name or "",
                "error_text": row.error_text or "",
                "started_at": _dt(row.started_at),
                "finished_at": _dt(row.finished_at),
                "duration_s": _duration_s(row.started_at, row.finished_at),
                "input_json": _json_dumps(_safe_json(row.input_json)),
                "output_json": _json_dumps(_safe_json(row.output_json)) if row.output_json is not None else "",
                "num_events": len(events),
                "num_tool_calls": sum(1 for event in events if event.event_type == "tool_call"),
                "num_tool_results_success": sum(
                    1 for event in events if event.event_type == "tool_result" and event.status == "success"
                ),
                "num_tool_results_error": sum(
                    1 for event in events if event.event_type == "tool_result" and event.status == "error"
                ),
                "num_llm_calls": len(llm_calls),
                "input_tokens_total": sum(call.input_tokens for call in llm_calls),
                "output_tokens_total": sum(call.output_tokens for call in llm_calls),
                "tokens_total": sum(call.tokens_total for call in llm_calls),
                "max_single_call_output_tokens": max((call.output_tokens for call in llm_calls), default=0),
                "had_recovered_tool_calls": any((call.text_recovered_tool_call_count or 0) > 0 for call in llm_calls),
                "failure_class": _classify_agent_failure(row) if row.status == "failed" else "",
                "output_preview": _preview(row.output_json),
            }
        )
    return rows


def _build_agent_event_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build agent event rows."""
    # Build the next value.
    return [
        {
            "agent_run_id": row.run_id,
            "agent_name": row.agent_name,
            "seq": row.seq,
            "event_type": row.event_type,
            "node_name": row.node_name or "",
            "tool_name": row.tool_name or "",
            "tool_call_id": row.tool_call_id or "",
            "status": row.status or "",
            "payload_preview": _preview(row.payload_text or row.payload_json),
            "payload_json": _json_dumps(_safe_json(row.payload_json)) if row.payload_json is not None else "",
            "payload_text": row.payload_text or "",
            "created_at": _dt(row.created_at),
        }
        for row in bundle.agent_events
    ]


def _build_agent_llm_call_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build agent LLM call rows."""
    # Build the next value.
    return [
        {
            "agent_run_id": row.run_id,
            "call_index": row.call_index,
            "iteration": row.iteration if row.iteration is not None else "",
            "agent_system": row.agent_system,
            "agent_name": row.agent_name,
            "model_name": row.model_name or "",
            "call_kind": row.call_kind,
            "started_at": _dt(row.started_at),
            "ended_at": _dt(row.ended_at),
            "latency_ms": row.latency_ms,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "tokens_total": row.tokens_total,
            "usage_source": row.usage_source,
            "cost_usd": row.cost_usd if row.cost_usd is not None else "",
            "had_tool_calls": row.had_tool_calls,
            "tool_call_count": row.tool_call_count if row.tool_call_count is not None else "",
            "tool_call_parse_source": row.tool_call_parse_source or "",
            "text_recovered_tool_call_count": row.text_recovered_tool_call_count,
            "native_tool_call_count": row.native_tool_call_count,
            "tool_names_json": _json_dumps(_safe_json(row.tool_names_json)) if row.tool_names_json is not None else "",
            "error_text": row.error_text or "",
        }
        for row in bundle.agent_llm_calls
    ]


def _build_tool_call_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build tool call rows."""
    # Build the next value.
    events_by_run: dict[str, list[AgentEvent]] = defaultdict(list)
    for row in bundle.agent_events:
        events_by_run[row.run_id].append(row)

    rows: list[dict[str, Any]] = []
    for run_id, events in events_by_run.items():
        for event in events:
            if event.event_type != "tool_call":
                continue
            result_event = None
            for candidate in events:
                if candidate.seq <= event.seq:
                    continue
                if candidate.event_type != "tool_result":
                    continue
                if candidate.tool_call_id and event.tool_call_id and candidate.tool_call_id == event.tool_call_id:
                    result_event = candidate
                    break
                if (
                    result_event is None
                    and not candidate.tool_call_id
                    and not event.tool_call_id
                    and candidate.tool_name == event.tool_name
                ):
                    result_event = candidate
                    break
            rows.append(
                {
                    "agent_run_id": run_id,
                    "agent_name": event.agent_name,
                    "tool_call_id": event.tool_call_id or "",
                    "tool_name": event.tool_name or "",
                    "call_seq": event.seq,
                    "result_seq": result_event.seq if result_event else "",
                    "result_status": result_event.status if result_event else "",
                    "call_payload_json": _json_dumps(_safe_json(event.payload_json)) if event.payload_json is not None else "",
                    "call_payload_preview": _preview(event.payload_text or event.payload_json),
                    "result_payload_json": _json_dumps(_safe_json(result_event.payload_json)) if result_event and result_event.payload_json is not None else "",
                    "result_payload_preview": _preview(
                        (result_event.payload_text or result_event.payload_json) if result_event else ""
                    ),
                    "result_error_text": result_event.payload_text if result_event and result_event.status == "error" else "",
                    "call_created_at": _dt(event.created_at),
                    "result_created_at": _dt(result_event.created_at) if result_event else "",
                }
            )
    return rows


def _build_metrics_rollup_rows(bundle: ExportBundle) -> list[dict[str, Any]]:
    """Build metrics rollup rows."""
    # Build the next value.
    rows: list[dict[str, Any]] = []

    by_agent: dict[str, list[AgentRun]] = defaultdict(list)
    for row in bundle.agent_runs:
        by_agent[row.agent_name].append(row)

    llm_by_run: dict[str, list[AgentLLMCall]] = defaultdict(list)
    for row in bundle.agent_llm_calls:
        llm_by_run[row.run_id].append(row)

    for agent_name, runs in sorted(by_agent.items()):
        failure_classes = Counter(_classify_agent_failure(run) for run in runs if run.status == "failed")
        total_input = sum(sum(call.input_tokens for call in llm_by_run.get(run.id, [])) for run in runs)
        total_output = sum(sum(call.output_tokens for call in llm_by_run.get(run.id, [])) for run in runs)
        total_llm_calls = sum(len(llm_by_run.get(run.id, [])) for run in runs)
        total_tool_calls = 0
        for run in runs:
            total_tool_calls += sum(1 for event in bundle.agent_events if event.run_id == run.id and event.event_type == "tool_call")
        rows.append(
            {
                "group_type": "agent_name",
                "group_key": agent_name,
                "run_count": len(runs),
                "failed_count": sum(1 for run in runs if run.status == "failed"),
                "succeeded_count": sum(1 for run in runs if run.status == "succeeded"),
                "avg_input_tokens": f"{(total_input / len(runs)):.2f}" if runs else "0.00",
                "avg_output_tokens": f"{(total_output / len(runs)):.2f}" if runs else "0.00",
                "avg_llm_calls": f"{(total_llm_calls / len(runs)):.2f}" if runs else "0.00",
                "avg_tool_calls": f"{(total_tool_calls / len(runs)):.2f}" if runs else "0.00",
                "most_common_failure": failure_classes.most_common(1)[0][0] if failure_classes else "",
            }
        )

    failure_counter = Counter(
        _classify_agent_failure(run) for run in bundle.agent_runs if run.status == "failed"
    )
    for failure_name, count in failure_counter.most_common():
        rows.append(
            {
                "group_type": "failure_class",
                "group_key": failure_name,
                "run_count": count,
                "failed_count": count,
                "succeeded_count": 0,
                "avg_input_tokens": "",
                "avg_output_tokens": "",
                "avg_llm_calls": "",
                "avg_tool_calls": "",
                "most_common_failure": failure_name,
            }
        )

    return rows


def _build_summary_markdown(bundle: ExportBundle) -> str:
    """Build summary markdown."""
    # Build the next value.
    total_case_runs = len(bundle.case_runs)
    succeeded_case_runs = sum(1 for row in bundle.case_runs if row.status == "succeeded")
    failed_case_runs = sum(1 for row in bundle.case_runs if row.status == "failed")
    success_rate = (succeeded_case_runs / total_case_runs) if total_case_runs else 0.0

    runs_by_agent: dict[str, list[AgentRun]] = defaultdict(list)
    for row in bundle.agent_runs:
        runs_by_agent[row.agent_name].append(row)

    failure_counter = Counter(
        _classify_agent_failure(row) for row in bundle.agent_runs if row.status == "failed"
    )

    lines: list[str] = []
    if bundle.mas_test_run:
        lines.append(f"# MAS Test Run Report: `{bundle.mas_test_run.id}`")
    else:
        lines.append(f"# MAS Run Group Report: `{bundle.report_id}`")
    lines.append("")
    lines.append("## Overview")
    lines.append(f"- Report kind: `{bundle.report_kind}`")
    lines.append(f"- Workflow: `{bundle.mas_test_run.workflow_id if bundle.mas_test_run else ''}`")
    lines.append(f"- Model: `{_model_name_for_bundle(bundle)}`")
    lines.append(f"- Status: `{bundle.mas_test_run.status if bundle.mas_test_run else ''}`")
    lines.append(
        f"- Selected cases: `{len(bundle.mas_test_run.selected_case_ids_json or []) if bundle.mas_test_run else len(bundle.mas_runs)}`"
    )
    lines.append(f"- MAS runs: `{len(bundle.mas_runs)}`")
    lines.append(f"- Case runs: `{total_case_runs}`")
    lines.append(f"- Succeeded case runs: `{succeeded_case_runs}`")
    lines.append(f"- Failed case runs: `{failed_case_runs}`")
    lines.append(f"- Success rate: `{success_rate:.1%}`")
    lines.append(f"- Started: `{_dt(bundle.mas_test_run.started_at) if bundle.mas_test_run else ''}`")
    lines.append(f"- Finished: `{_dt(bundle.mas_test_run.finished_at) if bundle.mas_test_run else ''}`")
    lines.append(
        f"- Duration (s): `{_duration_s(bundle.mas_test_run.started_at, bundle.mas_test_run.finished_at) if bundle.mas_test_run else ''}`"
    )
    lines.append("")

    lines.append("## Agent Breakdown")
    for agent_name, runs in sorted(runs_by_agent.items()):
        total_input = 0
        total_output = 0
        llm_count = 0
        for run in runs:
            for call in bundle.agent_llm_calls:
                if call.run_id == run.id:
                    total_input += call.input_tokens
                    total_output += call.output_tokens
                    llm_count += 1
        lines.append(
            f"- `{agent_name}`: runs=`{len(runs)}`, failed=`{sum(1 for run in runs if run.status == 'failed')}`, "
            f"succeeded=`{sum(1 for run in runs if run.status == 'succeeded')}`, llm_calls=`{llm_count}`, "
            f"input_tokens=`{total_input}`, output_tokens=`{total_output}`"
        )
    lines.append("")

    lines.append("## Top Failure Classes")
    if failure_counter:
        for name, count in failure_counter.most_common(10):
            lines.append(f"- `{name}`: `{count}`")
    else:
        lines.append("- No failed agent runs")
    lines.append("")

    lines.append("## Files")
    lines.append("- `mas_test_run.csv`")
    lines.append("- `mas_test_case_runs.csv`")
    lines.append("- `mas_runs.csv`")
    lines.append("- `mas_run_metrics.csv`")
    lines.append("- `mas_events.csv`")
    lines.append("- `mas_handoffs.csv`")
    lines.append("- `mas_final_outputs.csv`")
    lines.append("- `agent_runs.csv`")
    lines.append("- `agent_events.csv`")
    lines.append("- `agent_llm_calls.csv`")
    lines.append("- `tool_calls.csv`")
    lines.append("- `metrics_rollup.csv`")
    lines.append("")
    return "\n".join(lines)


def export_mas_test_run_report(mas_test_run_id: str, output_root: Path) -> Path:
    """Handle mas test run report."""
    # Keep the main step clear.
    bundle = _collect_bundle(mas_test_run_id)
    out_dir = output_root / bundle.report_id
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(out_dir / "mas_test_run.csv", _build_mas_test_run_rows(bundle))
    _write_csv(out_dir / "mas_test_case_runs.csv", _build_case_run_rows(bundle))
    _write_csv(out_dir / "mas_runs.csv", _build_mas_run_rows(bundle))
    _write_csv(out_dir / "mas_run_metrics.csv", _build_mas_metric_rows(bundle))
    _write_csv(out_dir / "mas_events.csv", _build_mas_event_rows(bundle))
    _write_csv(out_dir / "mas_handoffs.csv", _build_handoff_rows(bundle))
    _write_csv(out_dir / "mas_final_outputs.csv", _build_final_output_rows(bundle))
    _write_csv(out_dir / "agent_runs.csv", _build_agent_run_rows(bundle))
    _write_csv(out_dir / "agent_events.csv", _build_agent_event_rows(bundle))
    _write_csv(out_dir / "agent_llm_calls.csv", _build_agent_llm_call_rows(bundle))
    _write_csv(out_dir / "tool_calls.csv", _build_tool_call_rows(bundle))
    _write_csv(out_dir / "metrics_rollup.csv", _build_metrics_rollup_rows(bundle))
    (out_dir / "summary.md").write_text(_build_summary_markdown(bundle), encoding="utf-8")
    return out_dir


def export_mas_run_group_report(
    mas_run_ids: list[str],
    output_root: Path,
    *,
    label: str | None = None,
) -> Path:
    """Handle mas run group report."""
    # Keep the main step clear.
    bundle = _collect_bundle_for_mas_runs(mas_run_ids, label=label)
    out_dir = output_root / bundle.report_id
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(out_dir / "mas_test_run.csv", _build_mas_test_run_rows(bundle))
    _write_csv(out_dir / "mas_test_case_runs.csv", _build_case_run_rows(bundle))
    _write_csv(out_dir / "mas_runs.csv", _build_mas_run_rows(bundle))
    _write_csv(out_dir / "mas_run_metrics.csv", _build_mas_metric_rows(bundle))
    _write_csv(out_dir / "mas_events.csv", _build_mas_event_rows(bundle))
    _write_csv(out_dir / "mas_handoffs.csv", _build_handoff_rows(bundle))
    _write_csv(out_dir / "mas_final_outputs.csv", _build_final_output_rows(bundle))
    _write_csv(out_dir / "agent_runs.csv", _build_agent_run_rows(bundle))
    _write_csv(out_dir / "agent_events.csv", _build_agent_event_rows(bundle))
    _write_csv(out_dir / "agent_llm_calls.csv", _build_agent_llm_call_rows(bundle))
    _write_csv(out_dir / "tool_calls.csv", _build_tool_call_rows(bundle))
    _write_csv(out_dir / "metrics_rollup.csv", _build_metrics_rollup_rows(bundle))
    (out_dir / "summary.md").write_text(_build_summary_markdown(bundle), encoding="utf-8")
    return out_dir


def main() -> int:
    """Handle the value."""
    # Keep the main step clear.
    parser = argparse.ArgumentParser(description="Export a MAS test run report or a mas-run-group report.")
    parser.add_argument("mas_test_run_id", nargs="?", help="MAS test run id to export")
    parser.add_argument(
        "--mas-run-id",
        action="append",
        dest="mas_run_ids",
        default=[],
        help="MAS run id to include. Repeat for multiple mas runs.",
    )
    parser.add_argument(
        "--mas-run-ids-file",
        help="Path to a text file containing one mas run id per line.",
    )
    parser.add_argument(
        "--label",
        help="Folder/report label for mas-run-group exports.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help=f"Directory where the report folder will be written (default: {DEFAULT_OUTPUT_ROOT})",
    )
    args = parser.parse_args()

    mas_run_ids = [str(run_id).strip() for run_id in args.mas_run_ids if str(run_id).strip()]
    if args.mas_run_ids_file:
        file_path = Path(args.mas_run_ids_file).resolve()
        for line in file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                mas_run_ids.append(line)

    if mas_run_ids:
        output_dir = export_mas_run_group_report(
            mas_run_ids=mas_run_ids,
            output_root=Path(args.output_root).resolve(),
            label=args.label,
        )
    else:
        if not args.mas_test_run_id:
            raise ValueError("Provide a mas_test_run_id or at least one --mas-run-id.")
        output_dir = export_mas_test_run_report(
            mas_test_run_id=str(args.mas_test_run_id).strip(),
            output_root=Path(args.output_root).resolve(),
        )
    print(str(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
