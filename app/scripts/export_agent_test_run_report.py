from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select

from app.database import SessionLocal, ensure_runtime_schema_upgrades
from app.models.agent_run import AgentRun
from app.models.agent_run_metrics import AgentRunMetrics
from app.models.agent_test_case import AgentTestCase
from app.models.agent_test_case_run import AgentTestCaseRun
from app.models.agent_test_run import AgentTestRun


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "reports" / "agent_test_runs"


def _normalize_id(raw: str) -> str:
    text = str(raw).strip()
    if not text:
        return text
    try:
        return str(UUID(text))
    except Exception:
        return text


def _json_dumps(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, default=str)


def _dt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _duration_ms(started_at: datetime | None, finished_at: datetime | None) -> int | None:
    if started_at is None or finished_at is None:
        return None
    return max(0, int((finished_at - started_at).total_seconds() * 1000))


def _duration_s(started_at: datetime | None, finished_at: datetime | None) -> str:
    if started_at is None or finished_at is None:
        return ""
    return f"{(finished_at - started_at).total_seconds():.3f}"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _latest_agent_test_run_id() -> str:
    db = SessionLocal()
    try:
        row = db.scalar(
            select(AgentTestRun)
            .order_by(AgentTestRun.created_at.desc(), AgentTestRun.id.desc())
            .limit(1)
        )
        if row is None:
            raise ValueError("No agent_test_runs found.")
        return str(row.id)
    finally:
        db.close()


def export_agent_test_run_report(*, run_id: str, output_path: Path | None = None) -> Path:
    ensure_runtime_schema_upgrades()
    normalized_run_id = _normalize_id(run_id)

    db = SessionLocal()
    try:
        run = db.scalar(select(AgentTestRun).where(AgentTestRun.id == normalized_run_id))
        if run is None:
            raise ValueError(f"Agent test run not found: {normalized_run_id}")

        case_runs = list(
            db.scalars(
                select(AgentTestCaseRun)
                .where(AgentTestCaseRun.test_run_id == normalized_run_id)
                .order_by(AgentTestCaseRun.started_at, AgentTestCaseRun.created_at, AgentTestCaseRun.id)
            )
        )
        case_run_by_case_id = {row.test_case_id: row for row in case_runs}

        case_rows = list(
            db.scalars(
                select(AgentTestCase)
                .where(AgentTestCase.id.in_(run.selected_case_ids_json))
            )
        ) if run.selected_case_ids_json else []
        case_by_id = {row.id: row for row in case_rows}

        agent_run_ids = [row.agent_run_id for row in case_runs if row.agent_run_id]
        agent_rows = list(
            db.scalars(select(AgentRun).where(AgentRun.id.in_(agent_run_ids)))
        ) if agent_run_ids else []
        agent_run_by_id = {row.id: row for row in agent_rows}
        agent_metric_rows = list(
            db.scalars(select(AgentRunMetrics).where(AgentRunMetrics.run_id.in_(agent_run_ids)))
        ) if agent_run_ids else []
        agent_metrics_by_run_id = {row.run_id: row for row in agent_metric_rows}

        ordered_case_ids = list(run.selected_case_ids_json or [])
        rows: list[dict[str, Any]] = []
        for index, case_id in enumerate(ordered_case_ids, start=1):
            test_case = case_by_id.get(case_id)
            case_run = case_run_by_case_id.get(case_id)
            agent_run = agent_run_by_id.get(case_run.agent_run_id) if case_run and case_run.agent_run_id else None
            agent_metrics = agent_metrics_by_run_id.get(agent_run.id) if agent_run is not None else None

            case_started_at = case_run.started_at if case_run is not None else None
            case_finished_at = case_run.finished_at if case_run is not None else None
            case_metrics = dict(case_run.metrics_json or {}) if case_run is not None else {}

            rows.append(
                {
                    "test_run_id": run.id,
                    "test_run_name": run.name or "",
                    "agent_name": run.agent_name,
                    "model_name": run.model_name or "",
                    "test_run_status": run.status,
                    "test_run_started_at": _dt(run.started_at),
                    "test_run_finished_at": _dt(run.finished_at),
                    "test_case_index": index,
                    "test_case_id": case_id,
                    "test_case_name": test_case.name if test_case is not None else "",
                    "case_run_id": case_run.id if case_run is not None else "",
                    "case_run_status": case_run.status if case_run is not None else "",
                    "passed": case_run.passed if case_run is not None else "",
                    "score": case_run.score if case_run is not None else "",
                    "agent_run_id": agent_run.id if agent_run is not None else "",
                    "agent_run_status": agent_run.status if agent_run is not None else "",
                    "started_at": _dt(case_started_at),
                    "finished_at": _dt(case_finished_at),
                    "duration_ms": case_metrics.get("latency_ms")
                    or _duration_ms(case_started_at, case_finished_at)
                    or "",
                    "duration_s": _duration_s(case_started_at, case_finished_at),
                    "error_text": (case_run.error_text if case_run is not None else "") or "",
                    "diff_json": _json_dumps(case_run.diff_json if case_run is not None else None),
                    "metrics_json": _json_dumps(case_run.metrics_json if case_run is not None else None),
                    "input_json": _json_dumps(test_case.input_json if test_case is not None else None),
                    "expected_json": _json_dumps(test_case.expected_json if test_case is not None else None),
                    "agent_output_json": _json_dumps(agent_run.output_json if agent_run is not None else None),
                    "agent_error_text": (agent_run.error_text if agent_run is not None else "") or "",
                    "llm_call_count": agent_metrics.llm_call_count if agent_metrics is not None else "",
                    "tool_call_count": agent_metrics.tool_call_count if agent_metrics is not None else "",
                    "tool_error_count": agent_metrics.tool_error_count if agent_metrics is not None else "",
                    "reliability_issue_count": (
                        agent_metrics.reliability_issue_count if agent_metrics is not None else ""
                    ),
                    "reliability_error_count": (
                        agent_metrics.reliability_error_count if agent_metrics is not None else ""
                    ),
                    "finalization_failure_count": (
                        agent_metrics.finalization_failure_count if agent_metrics is not None else ""
                    ),
                    "tool_recovery_failure_count": (
                        agent_metrics.tool_recovery_failure_count if agent_metrics is not None else ""
                    ),
                    "input_tokens_total": agent_metrics.input_tokens_total if agent_metrics is not None else "",
                    "output_tokens_total": agent_metrics.output_tokens_total if agent_metrics is not None else "",
                    "tokens_total": agent_metrics.tokens_total if agent_metrics is not None else "",
                    "cost_usd_total": agent_metrics.cost_usd_total if agent_metrics is not None else "",
                    "schema_valid": agent_metrics.schema_valid if agent_metrics is not None else "",
                    "failure_reason": agent_metrics.failure_reason if agent_metrics is not None else "",
                }
            )

        if output_path is None:
            output_path = DEFAULT_OUTPUT_ROOT / normalized_run_id / "case_report.csv"

        fieldnames = [
            "test_run_id",
            "test_run_name",
            "agent_name",
            "model_name",
            "test_run_status",
            "test_run_started_at",
            "test_run_finished_at",
            "test_case_index",
            "test_case_id",
            "test_case_name",
            "case_run_id",
            "case_run_status",
            "passed",
            "score",
            "agent_run_id",
            "agent_run_status",
            "started_at",
            "finished_at",
            "duration_ms",
            "duration_s",
            "error_text",
            "diff_json",
            "metrics_json",
            "input_json",
            "expected_json",
            "agent_output_json",
            "agent_error_text",
            "llm_call_count",
            "tool_call_count",
            "tool_error_count",
            "reliability_issue_count",
            "reliability_error_count",
            "finalization_failure_count",
            "tool_recovery_failure_count",
            "input_tokens_total",
            "output_tokens_total",
            "tokens_total",
            "cost_usd_total",
            "schema_valid",
            "failure_reason",
        ]
        _write_csv(output_path, rows, fieldnames)
        return output_path
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export one single-agent test run to a spreadsheet-friendly CSV."
    )
    parser.add_argument(
        "--run-id",
        dest="run_id",
        help="Agent test run id to export.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Export the most recently created single-agent test run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output CSV path. Defaults to reports/agent_test_runs/<run_id>/case_report.csv",
    )
    args = parser.parse_args()

    run_id = _normalize_id(args.run_id) if args.run_id else ""
    if args.latest:
        run_id = _latest_agent_test_run_id()
    if not run_id:
        parser.error("Provide --run-id <id> or --latest.")

    output_path = export_agent_test_run_report(run_id=run_id, output_path=args.output)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
