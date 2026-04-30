from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.agent_event import AgentEvent
from app.models.agent_run import AgentRun
from app.models.mas_test_case import MasTestCase
from app.models.mas_test_case_run import MasTestCaseRun
from app.models.mas_test_run import MasTestRun
from app.models.swarm_run import SwarmRun


CSV_FIELDNAMES = [
    "mas_test_run_id",
    "mas_test_case_run_id",
    "swarm_run_id",
    "agent_run_id",
    "agent_name",
    "tool_call_name",
    "tool_call_output_json",
    "case_input_json",
    "tiragecase",
    "temperature",
    "heartrate",
    "resprate",
    "o2sat",
    "sbp",
    "dbp",
]


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _normalize_id(raw: str) -> str:
    text = str(raw).strip()
    if not text:
        return text
    try:
        return str(uuid.UUID(text))
    except Exception:
        return text


def _write_rows(output_path: Path, rows: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _string_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _build_case_columns(input_json: dict[str, Any] | None) -> dict[str, str]:
    payload = dict(input_json or {})
    return {
        "case_input_json": _json_dumps(payload) if payload else "",
        "tiragecase": _string_or_empty(payload.get("tiragecase")),
        "temperature": _string_or_empty(payload.get("temperature")),
        "heartrate": _string_or_empty(payload.get("heartrate")),
        "resprate": _string_or_empty(payload.get("resprate")),
        "o2sat": _string_or_empty(payload.get("o2sat")),
        "sbp": _string_or_empty(payload.get("sbp")),
        "dbp": _string_or_empty(payload.get("dbp")),
    }


def _build_tool_output_json(
    *,
    tool_call_event: AgentEvent,
) -> str:
    call_payload = dict(tool_call_event.payload_json or {})

    record = {
        "id": tool_call_event.tool_call_id,
        "name": str(tool_call_event.tool_name or ""),
        "arguments": call_payload.get("args"),
    }
    return _json_dumps({"tool_calls": [record]})


def _ordered_agent_runs_for_swarm(db, swarm_run_id: str) -> list[AgentRun]:
    return list(
        db.scalars(
            select(AgentRun)
            .where(AgentRun.swarm_run_id == swarm_run_id)
            .order_by(AgentRun.started_at, AgentRun.created_at, AgentRun.agent_name)
        )
    )


def _collect_rows_for_agent_runs(
    *,
    db,
    swarm_run_id: str,
    agent_runs: list[AgentRun],
    case_input_json: dict[str, Any] | None = None,
    mas_test_run_id: str | None = None,
    mas_test_case_run_id: str | None = None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    case_columns = _build_case_columns(case_input_json)

    for agent_run in agent_runs:
        events = list(
            db.scalars(
                select(AgentEvent)
                .where(AgentEvent.run_id == agent_run.id)
                .order_by(AgentEvent.seq)
            )
        )

        for event in events:
            if event.event_type != "tool_call":
                continue

            rows.append(
                {
                    "mas_test_run_id": mas_test_run_id or "",
                    "mas_test_case_run_id": mas_test_case_run_id or "",
                    "swarm_run_id": swarm_run_id,
                    "agent_run_id": agent_run.id,
                    "agent_name": agent_run.agent_name,
                    "tool_call_name": str(event.tool_name or ""),
                    "tool_call_output_json": _build_tool_output_json(
                        tool_call_event=event,
                    ),
                    **case_columns,
                }
            )

    return rows


def collect_swarm_tool_call_rows(
    *,
    swarm_run_id: str,
) -> tuple[list[dict[str, str]], int]:
    db = SessionLocal()
    try:
        swarm_run = db.scalar(select(SwarmRun).where(SwarmRun.id == swarm_run_id))
        if swarm_run is None:
            raise ValueError(f"Swarm run not found: {swarm_run_id}")

        agent_runs = _ordered_agent_runs_for_swarm(db, swarm_run_id)
        rows = _collect_rows_for_agent_runs(
            db=db,
            swarm_run_id=swarm_run_id,
            agent_runs=agent_runs,
            case_input_json=dict(swarm_run.input_json or {}),
        )
        return rows, len(agent_runs)
    finally:
        db.close()


def collect_mas_test_run_tool_call_rows(
    *,
    mas_test_run_id: str,
) -> tuple[list[dict[str, str]], int, int]:
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
        case_ids = [case_run.test_case_id for case_run in case_runs]
        case_rows = list(
            db.scalars(
                select(MasTestCase).where(MasTestCase.id.in_(case_ids))
            )
        ) if case_ids else []
        case_input_by_id = {row.id: dict(row.input_json or {}) for row in case_rows}

        rows: list[dict[str, str]] = []
        swarm_run_count = 0
        total_agent_runs = 0
        for case_run in case_runs:
            swarm_run_id = str(case_run.swarm_run_id or "").strip()
            if not swarm_run_id:
                continue
            if db.scalar(select(SwarmRun.id).where(SwarmRun.id == swarm_run_id)) is None:
                continue

            swarm_run_count += 1
            agent_runs = _ordered_agent_runs_for_swarm(db, swarm_run_id)
            total_agent_runs += len(agent_runs)
            rows.extend(
                _collect_rows_for_agent_runs(
                    db=db,
                    swarm_run_id=swarm_run_id,
                    agent_runs=agent_runs,
                    case_input_json=case_input_by_id.get(case_run.test_case_id),
                    mas_test_run_id=mas_test_run_id,
                    mas_test_case_run_id=case_run.id,
                )
            )

        return rows, swarm_run_count, total_agent_runs
    finally:
        db.close()


def collect_rows_by_run_id(
    *,
    run_id: str,
) -> tuple[list[dict[str, str]], str, int]:
    db = SessionLocal()
    try:
        normalized_id = _normalize_id(run_id)

        if db.scalar(select(MasTestRun.id).where(MasTestRun.id == normalized_id)) is not None:
            rows, swarm_run_count, agent_run_count = collect_mas_test_run_tool_call_rows(
                mas_test_run_id=normalized_id
            )
            return rows, f"mas_test_run ({swarm_run_count} swarm runs)", agent_run_count

        if db.scalar(select(SwarmRun.id).where(SwarmRun.id == normalized_id)) is not None:
            rows, agent_run_count = collect_swarm_tool_call_rows(swarm_run_id=normalized_id)
            return rows, "swarm_run", agent_run_count

        raise ValueError(f"Run id not found as swarm run or MAS test run: {run_id}")
    finally:
        db.close()


def _default_output_path(run_ids: list[str]) -> Path:
    if len(run_ids) == 1:
        suffix = run_ids[0]
    else:
        suffix = "batch"
    return Path("exports") / f"swarm_tool_calls_{suffix}.csv"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export tool calls to CSV for either a swarm run or a MAS test run. "
            "The tool_call_output_json column contains only the model-side tool call "
            "format: tool_calls -> id, name, arguments."
        )
    )
    parser.add_argument(
        "run_ids",
        nargs="+",
        help="One or more swarm run ids or MAS test run ids to export.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        help="CSV output path. Defaults to exports/swarm_tool_calls_<run_id>.csv for one id or exports/swarm_tool_calls_batch.csv for many ids",
    )
    args = parser.parse_args()

    run_ids = [_normalize_id(item) for item in args.run_ids if _normalize_id(item)]
    if not run_ids:
        print("at least one run_id must be non-empty", file=sys.stderr)
        return 2

    output_path = Path(args.output) if args.output else _default_output_path(run_ids)

    try:
        all_rows: list[dict[str, str]] = []
        summaries: list[str] = []
        total_agent_run_count = 0
        for run_id in run_ids:
            rows, run_kind, agent_run_count = collect_rows_by_run_id(run_id=run_id)
            all_rows.extend(rows)
            total_agent_run_count += agent_run_count
            summaries.append(f"{run_kind} {run_id}")
        _write_rows(output_path, all_rows)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Exported {len(all_rows)} tool-call rows from {total_agent_run_count} agent runs "
        f"for {len(run_ids)} run ids to {output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
