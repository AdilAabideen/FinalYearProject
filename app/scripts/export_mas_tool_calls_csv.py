"""Export Mas Tool Calls Csv script helpers."""

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

from langchain_core.messages import ToolMessage

from app.agentic.protocols.message_normalizer import render_tool_message_as_user_content
from app.database import SessionLocal
from app.models.agent_event import AgentEvent
from app.models.agent_run import AgentRun
from app.models.mas_test_case import MasTestCase
from app.models.mas_test_case_run import MasTestCaseRun
from app.models.mas_test_run import MasTestRun
from app.models.mas_run import MASRun


CSV_FIELDNAMES = [
    "mas_test_run_id",
    "mas_test_case_run_id",
    "mas_run_id",
    "agent_run_id",
    "agent_name",
    "tool_call_name",
    "tool_call_output_json",
    "tool_result_user_message",
    "case_input_json",
]

VITAL_INPUT_KEYS = ("temperature", "heartrate", "resprate", "o2sat", "sbp", "dbp")
ACUITY_AGENT_NAMES = {"esi1_agent", "esi2_agent", "esi345_agent"}


def _json_dumps(value: Any) -> str:
    """Handle dumps."""
    # Keep the main step clear.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _normalize_id(raw: str) -> str:
    """Normalize id."""
    # Keep the output consistent.
    text = str(raw).strip()
    if not text:
        return text
    try:
        return str(uuid.UUID(text))
    except Exception:
        return text


def _write_rows(output_path: Path, rows: list[dict[str, str]]) -> None:
    """Handle rows."""
    # Keep the main step clear.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _string_or_empty(value: Any) -> str:
    """Handle or empty."""
    # Keep the main step clear.
    if value is None:
        return ""
    return str(value)


def _case_input_for_agent(
    *,
    input_json: dict[str, Any] | None,
    agent_name: str,
) -> dict[str, Any]:
    """Handle input for agent."""
    # Keep the main step clear.
    payload = dict(input_json or {})
    if agent_name not in ACUITY_AGENT_NAMES:
        return payload
    for key in VITAL_INPUT_KEYS:
        payload.pop(key, None)
    return payload


def _build_case_columns(
    *,
    input_json: dict[str, Any] | None,
    agent_name: str,
) -> dict[str, str]:
    """Build case columns."""
    # Build the next value.
    payload = _case_input_for_agent(input_json=input_json, agent_name=agent_name)
    return {"case_input_json": _json_dumps(payload) if payload else ""}


def _build_tool_output_json(
    *,
    tool_call_event: AgentEvent,
) -> str:
    """Build tool output json."""
    # Build the next value.
    call_payload = dict(tool_call_event.payload_json or {})

    record = {
        "id": tool_call_event.tool_call_id,
        "name": str(tool_call_event.tool_name or ""),
        "arguments": call_payload.get("args"),
    }
    return _json_dumps({"tool_calls": [record]})


def _build_tool_result_user_message(
    *,
    tool_result_event: AgentEvent | None,
) -> str:
    """Build tool result user message."""
    # Build the next value.
    if tool_result_event is None:
        return ""

    if tool_result_event.payload_text is not None:
        raw_content = str(tool_result_event.payload_text or "").strip()
    elif tool_result_event.payload_json is not None:
        raw_content = _json_dumps(tool_result_event.payload_json.get("result"))
    else:
        raw_content = ""

    tool_message = ToolMessage(
        content=raw_content,
        tool_call_id=tool_result_event.tool_call_id,
        name=tool_result_event.tool_name,
        status=tool_result_event.status,
    )
    return render_tool_message_as_user_content(tool_message)


def _find_tool_result_event(
    *,
    events: list[AgentEvent],
    tool_call_event: AgentEvent,
) -> AgentEvent | None:
    """Handle tool result event."""
    # Keep the main step clear.
    for event in events:
        if event.seq <= tool_call_event.seq:
            continue
        if event.event_type != "tool_result":
            continue
        if event.tool_call_id and tool_call_event.tool_call_id:
            if event.tool_call_id == tool_call_event.tool_call_id:
                return event
            continue
        if event.tool_name and tool_call_event.tool_name and event.tool_name == tool_call_event.tool_name:
            return event
    return None


def _ordered_agent_runs_for_mas(db, mas_run_id: str) -> list[AgentRun]:
    """Handle agent runs for MAS."""
    # Keep the main step clear.
    return list(
        db.scalars(
            select(AgentRun)
            .where(AgentRun.mas_run_id == mas_run_id)
            .order_by(AgentRun.started_at, AgentRun.created_at, AgentRun.agent_name)
        )
    )


def _collect_rows_for_agent_runs(
    *,
    db,
    mas_run_id: str,
    agent_runs: list[AgentRun],
    case_input_json: dict[str, Any] | None = None,
    mas_test_run_id: str | None = None,
    mas_test_case_run_id: str | None = None,
) -> list[dict[str, str]]:
    """Handle rows for agent runs."""
    # Keep the main step clear.
    rows: list[dict[str, str]] = []

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
            case_columns = _build_case_columns(
                input_json=case_input_json,
                agent_name=agent_run.agent_name,
            )
            tool_result_event = _find_tool_result_event(events=events, tool_call_event=event)

            rows.append(
                {
                    "mas_test_run_id": mas_test_run_id or "",
                    "mas_test_case_run_id": mas_test_case_run_id or "",
                    "mas_run_id": mas_run_id,
                    "agent_run_id": agent_run.id,
                    "agent_name": agent_run.agent_name,
                    "tool_call_name": str(event.tool_name or ""),
                    "tool_call_output_json": _build_tool_output_json(
                        tool_call_event=event,
                    ),
                    "tool_result_user_message": _build_tool_result_user_message(
                        tool_result_event=tool_result_event,
                    ),
                    **case_columns,
                }
            )

    return rows


def collect_mas_tool_call_rows(
    *,
    mas_run_id: str,
) -> tuple[list[dict[str, str]], int]:
    """Handle mas tool call rows."""
    # Keep the main step clear.
    db = SessionLocal()
    try:
        mas_run = db.scalar(select(MASRun).where(MASRun.id == mas_run_id))
        if mas_run is None:
            raise ValueError(f"MAS run not found: {mas_run_id}")

        agent_runs = _ordered_agent_runs_for_mas(db, mas_run_id)
        rows = _collect_rows_for_agent_runs(
            db=db,
            mas_run_id=mas_run_id,
            agent_runs=agent_runs,
            case_input_json=dict(mas_run.input_json or {}),
        )
        return rows, len(agent_runs)
    finally:
        db.close()


def collect_mas_test_run_tool_call_rows(
    *,
    mas_test_run_id: str,
) -> tuple[list[dict[str, str]], int, int]:
    """Handle mas test run tool call rows."""
    # Keep the main step clear.
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
        mas_run_count = 0
        total_agent_runs = 0
        for case_run in case_runs:
            mas_run_id = str(case_run.mas_run_id or "").strip()
            if not mas_run_id:
                continue
            if db.scalar(select(MASRun.id).where(MASRun.id == mas_run_id)) is None:
                continue

            mas_run_count += 1
            agent_runs = _ordered_agent_runs_for_mas(db, mas_run_id)
            total_agent_runs += len(agent_runs)
            rows.extend(
                _collect_rows_for_agent_runs(
                    db=db,
                    mas_run_id=mas_run_id,
                    agent_runs=agent_runs,
                    case_input_json=case_input_by_id.get(case_run.test_case_id),
                    mas_test_run_id=mas_test_run_id,
                    mas_test_case_run_id=case_run.id,
                )
            )

        return rows, mas_run_count, total_agent_runs
    finally:
        db.close()


def collect_rows_by_run_id(
    *,
    run_id: str,
) -> tuple[list[dict[str, str]], str, int]:
    """Handle rows by run id."""
    # Keep the main step clear.
    db = SessionLocal()
    try:
        normalized_id = _normalize_id(run_id)

        if db.scalar(select(MasTestRun.id).where(MasTestRun.id == normalized_id)) is not None:
            rows, mas_run_count, agent_run_count = collect_mas_test_run_tool_call_rows(
                mas_test_run_id=normalized_id
            )
            return rows, f"mas_test_run ({mas_run_count} mas runs)", agent_run_count

        if db.scalar(select(MASRun.id).where(MASRun.id == normalized_id)) is not None:
            rows, agent_run_count = collect_mas_tool_call_rows(mas_run_id=normalized_id)
            return rows, "mas_run", agent_run_count

        raise ValueError(f"Run id not found as mas run or MAS test run: {run_id}")
    finally:
        db.close()


def _default_output_path(run_ids: list[str]) -> Path:
    """Handle output path."""
    # Keep the main step clear.
    if len(run_ids) == 1:
        suffix = run_ids[0]
    else:
        suffix = "batch"
    return Path("exports") / f"mas_tool_calls_{suffix}.csv"


def main() -> int:
    """Handle the value."""
    # Keep the main step clear.
    parser = argparse.ArgumentParser(
        description=(
            "Export tool calls to CSV for either a mas run or a MAS test run. "
            "The tool_call_output_json column contains only the model-side tool call "
            "format, and tool_result_user_message contains the rendered tool result "
            "replayed back as a user message."
        )
    )
    parser.add_argument(
        "run_ids",
        nargs="+",
        help="One or more mas run ids or MAS test run ids to export.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        help="CSV output path. Defaults to exports/mas_tool_calls_<run_id>.csv for one id or exports/mas_tool_calls_batch.csv for many ids",
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
