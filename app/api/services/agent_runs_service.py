from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from time import sleep
from typing import Any, Optional, Tuple

from fastapi import BackgroundTasks, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agentic.agents.agents import get_agent_spec, supported_agent_names
from app.agentic.model_registry import get_chat_model, validate_model_for_agent
from app.agentic.runtime import AgentRuntime
from app.agentic.runtime.failure_taxonomy import FailureCategory
from app.api.repository import agent_metrics_repository, agent_runs_repository
from app.config import settings
from app.database import SessionLocal
from app.models.agent_run import AgentRun
from app.schemas.agent_runs import (
    AgentEventRead,
    AgentEventsPage,
    AgentLLMCallRead,
    AgentRunCreateRequest,
    AgentRunCreateResponse,
    AgentRunReliabilityIssuePage,
    AgentRunReliabilityIssueRead,
    AgentRunReliabilityCategoryCount,
    AgentRunReliabilitySummary,
    AgentRunMetricsDetail,
    AgentRunMetricsRead,
    AgentRunMetricsSummary,
    AgentRunRead,
    AgentToolCallRead,
    RunStatus,
)

MAX_EVENT_TEXT_LEN = 50_000
MAX_RELIABILITY_SCAN_EVENTS = 50_000


@dataclass
class _ReliabilityIssue:
    issue_code: str
    severity: str
    stage: str
    message: str
    details_json: Optional[dict[str, Any]] = None
    assistant_raw_text: Optional[str] = None
    iteration: Optional[int] = None
    call_index: Optional[int] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None


def _safe_text(text: str) -> str:
    if len(text) <= MAX_EVENT_TEXT_LEN:
        return text
    return text[:MAX_EVENT_TEXT_LEN] + "…(truncated)"


def _try_parse_json(text: str) -> Tuple[Optional[dict], Optional[str]]:
    stripped = text.strip()
    if not stripped:
        return None, ""
    try:
        parsed = json.loads(stripped)
    except Exception:
        return None, stripped
    if isinstance(parsed, dict):
        return parsed, None
    return {"value": parsed}, None


def _append_event(
    *,
    db: Session,
    run: AgentRun,
    seq: int,
    event_type: str,
    node_name: Optional[str] = None,
    tool_name: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    status: Optional[str] = None,
    payload_json: Optional[dict] = None,
    payload_text: Optional[str] = None,
) -> None:
    agent_runs_repository.append_event(
        db,
        run_id=run.id,
        agent_name=run.agent_name,
        seq=seq,
        event_type=event_type,
        node_name=node_name,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        status=status,
        payload_json=payload_json,
        payload_text=_safe_text(payload_text) if payload_text else None,
        created_at=datetime.utcnow(),
    )


def _coerce_output_json(value: Any) -> Optional[dict]:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump") and callable(value.model_dump):
        try:
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return dumped
            return {"value": dumped}
        except Exception:
            pass
    if isinstance(value, str):
        parsed, _ = _try_parse_json(value)
        return parsed
    return {"value": value}


def _truncate_optional_text(value: Optional[str], max_len: int = 4_000) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…(truncated)"


def _schema_validation_error(run: AgentRun, output_json: Optional[dict]) -> Optional[str]:
    if output_json is None:
        return None
    try:
        spec = get_agent_spec(run.agent_name)
    except Exception:
        return None
    if spec.output_model is None:
        return None
    try:
        spec.output_model.model_validate(output_json)
        return None
    except Exception as exc:
        return str(exc)


def _collect_reliability_issues(
    *,
    db: Session,
    run: AgentRun,
    output_json: Optional[dict],
    raw_output: Any,
) -> list[_ReliabilityIssue]:
    llm_calls = agent_metrics_repository.list_llm_calls(db, run.id)
    tool_calls = agent_metrics_repository.list_tool_calls(db, run.id)
    events = agent_runs_repository.list_events_after(
        db,
        run_id=run.id,
        after_seq=0,
        limit=MAX_RELIABILITY_SCAN_EVENTS,
    )

    issues: list[_ReliabilityIssue] = []

    assistant_tool_parse_event_ids: list[int] = []
    for ev in events:
        if ev.event_type != "assistant":
            continue
        raw_text = str(ev.payload_text or "").strip()
        has_tool_calls_text = "tool_calls" in raw_text.lower()
        if has_tool_calls_text and ev.payload_json is None:
            assistant_tool_parse_event_ids.append(int(ev.seq))
            issues.append(
                _ReliabilityIssue(
                    issue_code=FailureCategory.NATIVE_TOOL_PARSE_FAILURE.value,
                    severity="warning",
                    stage="tool_recovery",
                    message="Assistant output looked like tool calls but could not be parsed as JSON.",
                    details_json={"event_seq": int(ev.seq)},
                    assistant_raw_text=_truncate_optional_text(raw_text),
                )
            )

    last_llm = llm_calls[-1] if llm_calls else None
    last_iteration = last_llm.iteration if last_llm is not None else None
    related_tool_calls = [
        {
            "id": t.tool_call_id,
            "name": t.tool_name,
            "status": t.status,
            "iteration": t.iteration,
        }
        for t in tool_calls
        if last_iteration is not None and t.iteration == last_iteration
    ]
    if not related_tool_calls:
        related_tool_calls = [
            {
                "id": t.tool_call_id,
                "name": t.tool_name,
                "status": t.status,
                "iteration": t.iteration,
            }
            for t in tool_calls[-5:]
        ]

    # Category: text_recovery_used
    text_recovered_total = sum(int(c.text_recovered_tool_call_count or 0) for c in llm_calls)
    if text_recovered_total > 0:
        issues.append(
            _ReliabilityIssue(
                issue_code=FailureCategory.TEXT_RECOVERY_USED.value,
                severity="info",
                stage="tool_recovery",
                message="Text-based tool-call recovery was used.",
                details_json={"text_recovered_tool_call_count": int(text_recovered_total)},
                iteration=last_iteration,
                call_index=(last_llm.call_index if last_llm is not None else None),
            )
        )

    # Category: unknown_tool / tool_execution_error
    unknown_tool_rows = [t for t in tool_calls if str(t.status or "").lower() == "error" and str(t.error_text or "").startswith("Unknown tool:")]
    tool_exec_error_rows = [
        t
        for t in tool_calls
        if str(t.status or "").lower() == "error" and t not in unknown_tool_rows
    ]
    if unknown_tool_rows:
        issues.append(
            _ReliabilityIssue(
                issue_code=FailureCategory.UNKNOWN_TOOL.value,
                severity="error",
                stage="tool_execution",
                message="One or more tool calls referenced unknown tools.",
                details_json={"count": len(unknown_tool_rows)},
                iteration=unknown_tool_rows[-1].iteration if unknown_tool_rows[-1].iteration is not None else last_iteration,
                tool_call_id=unknown_tool_rows[-1].tool_call_id,
                tool_name=unknown_tool_rows[-1].tool_name,
            )
        )
    if tool_exec_error_rows:
        issues.append(
            _ReliabilityIssue(
                issue_code=FailureCategory.TOOL_EXECUTION_ERROR.value,
                severity="error",
                stage="tool_execution",
                message="One or more tool calls failed during execution.",
                details_json={"count": len(tool_exec_error_rows)},
                iteration=tool_exec_error_rows[-1].iteration if tool_exec_error_rows[-1].iteration is not None else last_iteration,
                tool_call_id=tool_exec_error_rows[-1].tool_call_id,
                tool_name=tool_exec_error_rows[-1].tool_name,
            )
        )

    # Category: extra_tool_calls_dropped
    executed_by_iteration: dict[int, int] = {}
    for t in tool_calls:
        it = int(t.iteration or 0)
        executed_by_iteration[it] = executed_by_iteration.get(it, 0) + 1
    dropped_total = 0
    for c in llm_calls:
        it = int(c.iteration or 0)
        planned = int(c.tool_call_count or 0)
        if planned <= 0:
            continue
        executed = int(executed_by_iteration.get(it, 0))
        if planned > executed:
            dropped_total += planned - executed
    if dropped_total > 0:
        issues.append(
            _ReliabilityIssue(
                issue_code=FailureCategory.EXTRA_TOOL_CALLS_DROPPED.value,
                severity="warning",
                stage="tool_execution",
                message="Some tool calls were dropped due to per-turn limits.",
                details_json={"dropped_tool_call_count": int(dropped_total)},
                iteration=last_iteration,
                call_index=(last_llm.call_index if last_llm is not None else None),
            )
        )

    if output_json is None:
        raw_output_text = str(raw_output).strip() if isinstance(raw_output, str) else ""
        latest_assistant_text = ""
        latest_assistant_seq: Optional[int] = None
        for ev in reversed(events):
            if ev.event_type != "assistant":
                continue
            latest_assistant_seq = int(ev.seq)
            latest_assistant_text = str(ev.payload_text or "").strip()
            if latest_assistant_text:
                break

        final_raw_text = raw_output_text or latest_assistant_text
        issue_code = (
            FailureCategory.FINAL_OUTPUT_INVALID.value
            if final_raw_text
            else FailureCategory.FINAL_OUTPUT_MISSING.value
        )
        issues.append(
            _ReliabilityIssue(
                issue_code=issue_code,
                severity="error",
                stage="finalization",
                message=(
                    "Run ended without a parseable final JSON output."
                    if issue_code == FailureCategory.FINAL_OUTPUT_INVALID.value
                    else "Run ended without any final output."
                ),
                details_json={
                    "latest_assistant_seq": latest_assistant_seq,
                    "related_tool_calls": related_tool_calls,
                },
                assistant_raw_text=_truncate_optional_text(final_raw_text),
                iteration=last_iteration,
                call_index=(last_llm.call_index if last_llm is not None else None),
                tool_call_id=(related_tool_calls[0]["id"] if len(related_tool_calls) == 1 else None),
                tool_name=(related_tool_calls[0]["name"] if len(related_tool_calls) == 1 else None),
            )
        )

        contains_tool_calls_hint = "tool_calls" in final_raw_text.lower() if final_raw_text else False
        if contains_tool_calls_hint or assistant_tool_parse_event_ids:
            issues.append(
                _ReliabilityIssue(
                    issue_code=FailureCategory.TEXT_RECOVERY_FAILURE.value,
                    severity="error",
                    stage="tool_recovery",
                    message="Tool-call recovery failed before finalization.",
                    details_json={
                        "event_seqs": assistant_tool_parse_event_ids,
                        "related_tool_calls": related_tool_calls,
                    },
                    assistant_raw_text=_truncate_optional_text(final_raw_text),
                    iteration=last_iteration,
                    call_index=(last_llm.call_index if last_llm is not None else None),
                )
            )
    else:
        schema_error = _schema_validation_error(run, output_json)
        if schema_error:
            issues.append(
                _ReliabilityIssue(
                    issue_code=FailureCategory.SCHEMA_VALIDATION_ERROR.value,
                    severity="warning",
                    stage="finalization",
                    message="Final output failed schema validation.",
                    details_json={"validation_error": _truncate_optional_text(schema_error, max_len=2_000)},
                    iteration=last_iteration,
                    call_index=(last_llm.call_index if last_llm is not None else None),
                )
            )

    return issues


def _persist_reliability_issues(
    *,
    db: Session,
    run: AgentRun,
    seq: int,
    issues: list[_ReliabilityIssue],
) -> int:
    if not issues:
        return seq

    for issue in issues:
        agent_metrics_repository.append_reliability_issue(
            db,
            run_id=run.id,
            agent_name=run.agent_name,
            model_name=run.model_name,
            issue_code=issue.issue_code,
            severity=issue.severity,
            stage=issue.stage,
            message=issue.message,
            details_json=issue.details_json,
            assistant_raw_text=issue.assistant_raw_text,
            iteration=issue.iteration,
            call_index=issue.call_index,
            tool_call_id=issue.tool_call_id,
            tool_name=issue.tool_name,
            created_at=datetime.utcnow(),
        )

        seq += 1
        _append_event(
            db=db,
            run=run,
            seq=seq,
            event_type="error",
            status=issue.severity,
            tool_name=issue.tool_name,
            tool_call_id=issue.tool_call_id,
            payload_json={
                "reliability_issue": {
                    "issue_code": issue.issue_code,
                    "stage": issue.stage,
                    "message": issue.message,
                    "details": issue.details_json,
                }
            },
            payload_text=issue.assistant_raw_text if issue.assistant_raw_text else None,
        )
    return seq


def _build_reliability_summary(db: Session, run_id: str) -> AgentRunReliabilitySummary:
    by_category = agent_metrics_repository.list_reliability_issue_category_counts(db, run_id)
    total_issues, error_issues, _, _ = agent_metrics_repository.count_reliability_issues(db, run_id)
    warning_issues = sum(count for _, severity, count in by_category if severity == "warning")
    info_issues = sum(count for _, severity, count in by_category if severity == "info")
    return AgentRunReliabilitySummary(
        total_issues=total_issues,
        error_issues=error_issues,
        warning_issues=warning_issues,
        info_issues=info_issues,
        by_category=[
            AgentRunReliabilityCategoryCount(issue_code=code, severity=severity, count=count)
            for code, severity, count in sorted(by_category, key=lambda item: (item[0], item[1]))
        ],
    )


def _resolve_agent_system(agent: Any) -> str:
    if all(hasattr(agent, attr) for attr in ("set_event_context", "set_event_handlers")):
        return "handrolled_callback"
    return "legacy_stream"


def _cost_from_tokens(
    *,
    model_spec: Any,
    input_tokens: int,
    output_tokens: int,
) -> Optional[float]:
    pricing = getattr(model_spec, "pricing", None)
    if pricing is None:
        return None
    input_price = getattr(pricing, "input_per_1k", None)
    output_price = getattr(pricing, "output_per_1k", None)
    if input_price is None and output_price is None:
        return None
    in_cost = (max(0, int(input_tokens)) / 1000.0) * float(input_price or 0.0)
    out_cost = (max(0, int(output_tokens)) / 1000.0) * float(output_price or 0.0)
    return in_cost + out_cost


def _schema_valid_for_run(run: AgentRun) -> Optional[bool]:
    if run.output_json is None:
        return None
    try:
        spec = get_agent_spec(run.agent_name)
    except Exception:
        return None
    if spec.output_model is None:
        return None
    try:
        spec.output_model.model_validate(run.output_json)
        return True
    except Exception:
        return False


def _persist_run_metrics(db: Session, run: AgentRun, *, agent_system: str) -> None:
    llm_calls = agent_metrics_repository.list_llm_calls(db, run.id)
    input_tokens_total = sum(int(c.input_tokens or 0) for c in llm_calls)
    output_tokens_total = sum(int(c.output_tokens or 0) for c in llm_calls)
    tokens_total = sum(int(c.tokens_total or 0) for c in llm_calls)
    cost_values = [c.cost_usd for c in llm_calls if c.cost_usd is not None]
    cost_usd_total = sum(cost_values) if cost_values else None
    llm_call_count = len(llm_calls)
    tool_call_count, tool_error_count = agent_metrics_repository.count_tool_events(db, run.id)
    (
        reliability_issue_count,
        reliability_error_count,
        finalization_failure_count,
        tool_recovery_failure_count,
    ) = agent_metrics_repository.count_reliability_issues(db, run.id)

    duration_ms: Optional[int] = None
    if run.started_at and run.finished_at:
        duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

    failure_reason: Optional[str] = None
    if run.status == "failed":
        err = (run.error_text or "").lower()
        failure_reason = (
            FailureCategory.TIMEOUT_ERROR.value
            if "timeout" in err
            else FailureCategory.PROVIDER_ERROR.value
        )

    agent_metrics_repository.upsert_run_metrics(
        db,
        run_id=run.id,
        agent_system=agent_system,
        agent_name=run.agent_name,
        model_name=run.model_name,
        status=run.status,
        failure_reason=failure_reason,
        duration_ms=duration_ms,
        llm_call_count=llm_call_count,
        tool_call_count=tool_call_count,
        tool_error_count=tool_error_count,
        reliability_issue_count=reliability_issue_count,
        reliability_error_count=reliability_error_count,
        finalization_failure_count=finalization_failure_count,
        tool_recovery_failure_count=tool_recovery_failure_count,
        input_tokens_total=input_tokens_total,
        output_tokens_total=output_tokens_total,
        tokens_total=tokens_total,
        cost_usd_total=cost_usd_total,
        schema_valid=_schema_valid_for_run(run),
    )


def _build_run_read(run: AgentRun, db: Session) -> AgentRunRead:
    metrics = agent_metrics_repository.get_run_metrics(db, run.id)
    model = AgentRunRead.model_validate(run.__dict__)
    if metrics is not None:
        model.metrics = AgentRunMetricsRead.model_validate(metrics.__dict__)
    return model


def _percentile(values: list[float], pct: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    rank = (pct / 100.0) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    frac = rank - lower
    return float(ordered[lower] * (1 - frac) + ordered[upper] * frac)


def _normalize_tool_names(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(name) for name in raw if name is not None]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(name) for name in parsed if name is not None]
        except Exception:
            return []
    return []


def _ensure_run_start_event(db: Session, run: AgentRun) -> int:
    seq = agent_runs_repository.get_last_event_seq(db, run.id)
    if seq > 0:
        return seq

    now = datetime.utcnow()
    if run.status != "running":
        run.status = "running"
    if run.started_at is None:
        run.started_at = now
    run.updated_at = now
    agent_runs_repository.save_run(db, run)

    _append_event(
        db=db,
        run=run,
        seq=1,
        event_type="run_start",
        payload_json={"input": run.input_json},
    )
    return 1


def execute_agent_run_and_persist(db: Session, run: AgentRun) -> Optional[dict]:
    seq = _ensure_run_start_event(db, run)
    agent_system = "unknown"

    try:
        seq, output_json, raw_output, agent_system = _run_agent_and_persist(db, run, seq)
        reliability_issues = _collect_reliability_issues(
            db=db,
            run=run,
            output_json=output_json,
            raw_output=raw_output,
        )
        seq = _persist_reliability_issues(
            db=db,
            run=run,
            seq=seq,
            issues=reliability_issues,
        )

        now = datetime.utcnow()
        run.status = "succeeded"
        run.output_json = output_json
        run.error_text = None
        run.finished_at = now
        run.updated_at = now
        agent_runs_repository.save_run(db, run)

        seq += 1
        _append_event(
            db=db,
            run=run,
            seq=seq,
            event_type="run_end",
            payload_json={"status": run.status},
        )
        _persist_run_metrics(db, run, agent_system=agent_system)
        return output_json
    except Exception as e:
        now = datetime.utcnow()
        run.status = "failed"
        run.error_text = str(e)
        run.finished_at = now
        run.updated_at = now
        agent_runs_repository.save_run(db, run)

        seq = agent_runs_repository.get_last_event_seq(db, run.id)
        seq += 1
        _append_event(
            db=db,
            run=run,
            seq=seq,
            event_type="error",
            status="error",
            payload_text=str(e),
        )
        seq += 1
        _append_event(
            db=db,
            run=run,
            seq=seq,
            event_type="run_end",
            payload_json={"status": run.status},
        )
        _persist_run_metrics(db, run, agent_system=agent_system)
        return None


def _run_agent_and_persist(db: Session, run: AgentRun, seq: int) -> Tuple[int, Optional[dict], Any, str]:
    try:
        spec = get_agent_spec(run.agent_name)
    except KeyError as e:
        raise RuntimeError(f"Unsupported agent_name '{run.agent_name}'") from e

    model_id = run.model_name or settings.OPENAI_MODEL
    model_spec = validate_model_for_agent(
        model_id=model_id,
        agent_name=run.agent_name,
        requires_tools=bool(spec.tools),
    )
    validated_input = spec.input_model.model_validate(run.input_json)
    runtime = AgentRuntime(
        model_id=model_id,
        model_spec=model_spec,
        model=get_chat_model(model_id),
    )
    agent = spec.build(runtime)
    agent_system = _resolve_agent_system(agent)
    payload = {"messages": [("user", validated_input.model_dump_json())]}

    def _normalize_payload_json(raw: Any) -> Optional[dict]:
        if raw is None:
            return None
        if isinstance(raw, dict):
            return raw
        return {"value": raw}

    def _persist_callback_event(item: dict[str, Any]) -> None:
        event_seq = int(item.get("seq"))
        _append_event(
            db=db,
            run=run,
            seq=event_seq,
            event_type=str(item.get("event_type") or ""),
            node_name=item.get("node_name"),
            tool_name=item.get("tool_name"),
            tool_call_id=item.get("tool_call_id"),
            status=item.get("status"),
            payload_json=_normalize_payload_json(item.get("payload_json")),
            payload_text=item.get("payload_text"),
        )

    def _persist_llm_call(item: dict[str, Any]) -> None:
        input_tokens = int(item.get("input_tokens") or 0)
        output_tokens = int(item.get("output_tokens") or 0)
        total_tokens = int(item.get("tokens_total") or (input_tokens + output_tokens))
        cost_usd = _cost_from_tokens(
            model_spec=model_spec,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        agent_metrics_repository.append_llm_call(
            db,
            run_id=run.id,
            call_index=int(item.get("call_index") or 0),
            agent_system=agent_system,
            agent_name=run.agent_name,
            model_name=item.get("model_name") or run.model_name,
            call_kind=str(item.get("call_kind") or "main_loop"),
            iteration=(int(item.get("iteration")) if item.get("iteration") is not None else None),
            started_at=item.get("started_at") or datetime.utcnow(),
            ended_at=item.get("ended_at") or datetime.utcnow(),
            latency_ms=int(item.get("latency_ms") or 0),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tokens_total=total_tokens,
            usage_source=str(item.get("usage_source") or "estimated"),
            cost_usd=cost_usd,
            had_tool_calls=(bool(item.get("had_tool_calls")) if item.get("had_tool_calls") is not None else None),
            tool_call_count=(int(item.get("tool_call_count")) if item.get("tool_call_count") is not None else None),
            tool_call_parse_source=(
                str(item.get("tool_call_parse_source")) if item.get("tool_call_parse_source") else None
            ),
            text_recovered_tool_call_count=int(item.get("text_recovered_tool_call_count") or 0),
            native_tool_call_count=int(item.get("native_tool_call_count") or 0),
            tool_names=_normalize_tool_names(item.get("tool_names")),
            error_text=item.get("error_text"),
        )

    def _persist_tool_call(item: dict[str, Any]) -> None:
        agent_metrics_repository.append_tool_call(
            db,
            run_id=run.id,
            agent_name=run.agent_name,
            iteration=int(item.get("iteration") or 0),
            tool_call_id=(str(item.get("tool_call_id")) if item.get("tool_call_id") else None),
            tool_name=str(item.get("tool_name") or "tool"),
            started_at=item.get("started_at") or datetime.utcnow(),
            ended_at=item.get("ended_at") or datetime.utcnow(),
            latency_ms=int(item.get("latency_ms") or 0),
            status=str(item.get("status") or "error"),
            result_char_count=int(item.get("result_char_count") or 0),
            result_estimated_tokens=int(item.get("result_estimated_tokens") or 0),
            error_text=item.get("error_text"),
        )

    supports_callbacks = all(hasattr(agent, attr) for attr in ("set_event_context", "set_event_handlers"))
    if not supports_callbacks:
        raise RuntimeError("Agent does not support callback event persistence")

    agent.set_event_context(run_id=run.id, agent_name=run.agent_name, start_seq=seq)
    agent.set_event_handlers([_persist_callback_event])
    if hasattr(agent, "set_llm_call_handlers"):
        agent.set_llm_call_handlers([_persist_llm_call])
    if hasattr(agent, "set_tool_call_handlers"):
        agent.set_tool_call_handlers([_persist_tool_call])
    if hasattr(agent, "run_timeout_s"):
        agent.run_timeout_s = float(settings.AGENT_RUN_TIMEOUT_S)

    output = asyncio.run(agent.ainvoke(payload))
    output_json = _coerce_output_json(output)
    seq = agent_runs_repository.get_last_event_seq(db, run.id)
    return seq, output_json, output, agent_system


def _execute_run_in_background(run_id: str) -> None:
    db = SessionLocal()
    try:
        run = agent_runs_repository.get_run(db, run_id)
        if run is None or run.status != "running":
            return
        execute_agent_run_and_persist(db, run)
    finally:
        db.close()


def create_agent_run(payload: AgentRunCreateRequest, db: Session) -> AgentRunCreateResponse:
    supported = supported_agent_names()
    if payload.agent_name not in supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported agent_name '{payload.agent_name}'. Supported: {sorted(supported)}",
        )

    spec = get_agent_spec(payload.agent_name)
    model_id = payload.model_id or settings.OPENAI_MODEL
    try:
        validate_model_for_agent(
            model_id=model_id,
            agent_name=payload.agent_name,
            requires_tools=bool(spec.tools),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = AgentRun(
        id=run_id,
        swarm_run_id=payload.swarm_run_id,
        workflow_id=payload.workflow_id,
        workflow_version=payload.workflow_version,
        sequence_index=payload.sequence_index,
        parent_handoff_id=payload.parent_handoff_id,
        outgoing_handoff_id=payload.outgoing_handoff_id,
        is_final_agent=payload.is_final_agent,
        agent_name=payload.agent_name,
        status="created",
        model_name=model_id,
        input_json=payload.input,
        started_at=None,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    agent_runs_repository.save_run(db, run)

    return AgentRunCreateResponse(run_id=run_id, status="created")


def start_agent_run(
    payload: AgentRunCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session,
) -> AgentRunCreateResponse:
    supported = supported_agent_names()
    if payload.agent_name not in supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported agent_name '{payload.agent_name}'. Supported: {sorted(supported)}",
        )

    spec = get_agent_spec(payload.agent_name)
    model_id = payload.model_id or settings.OPENAI_MODEL
    try:
        validate_model_for_agent(
            model_id=model_id,
            agent_name=payload.agent_name,
            requires_tools=bool(spec.tools),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = AgentRun(
        id=run_id,
        swarm_run_id=payload.swarm_run_id,
        workflow_id=payload.workflow_id,
        workflow_version=payload.workflow_version,
        sequence_index=payload.sequence_index,
        parent_handoff_id=payload.parent_handoff_id,
        outgoing_handoff_id=payload.outgoing_handoff_id,
        is_final_agent=payload.is_final_agent,
        agent_name=payload.agent_name,
        status="running",
        model_name=model_id,
        input_json=payload.input,
        started_at=now,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    agent_runs_repository.save_run(db, run)

    _append_event(
        db=db,
        run=run,
        seq=1,
        event_type="run_start",
        payload_json={"input": run.input_json},
    )

    background_tasks.add_task(_execute_run_in_background, run_id)
    return AgentRunCreateResponse(run_id=run_id, status="running")


def get_agent_run(run_id: str, db: Session) -> AgentRunRead:
    run = agent_runs_repository.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return _build_run_read(run, db)


def get_agent_run_metrics(run_id: str, db: Session) -> AgentRunMetricsDetail:
    run = agent_runs_repository.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    metrics_row = agent_metrics_repository.get_run_metrics(db, run_id)
    llm_calls = agent_metrics_repository.list_llm_calls(db, run_id)
    tool_calls = agent_metrics_repository.list_tool_calls(db, run_id)

    llm_items = [
        AgentLLMCallRead(
            id=c.id,
            run_id=c.run_id,
            call_index=c.call_index,
            agent_system=c.agent_system,
            agent_name=c.agent_name,
            model_name=c.model_name,
            call_kind=c.call_kind,
            iteration=c.iteration,
            started_at=c.started_at,
            ended_at=c.ended_at,
            latency_ms=c.latency_ms,
            input_tokens=c.input_tokens,
            output_tokens=c.output_tokens,
            tokens_total=c.tokens_total,
            usage_source=c.usage_source,
            had_tool_calls=c.had_tool_calls,
            tool_call_count=c.tool_call_count,
            tool_call_parse_source=c.tool_call_parse_source,
            text_recovered_tool_call_count=int(c.text_recovered_tool_call_count or 0),
            native_tool_call_count=int(c.native_tool_call_count or 0),
            tool_names=_normalize_tool_names(c.tool_names_json),
            cost_usd=c.cost_usd,
            error_text=c.error_text,
        )
        for c in llm_calls
    ]

    tool_items = [AgentToolCallRead.model_validate(t.__dict__) for t in tool_calls]

    return AgentRunMetricsDetail(
        run_id=run_id,
        metrics=(
            AgentRunMetricsRead.model_validate(metrics_row.__dict__)
            if metrics_row is not None
            else None
        ),
        llm_calls=llm_items,
        tool_calls=tool_items,
        reliability_summary=_build_reliability_summary(db, run_id),
    )


def get_agent_run_reliability_issues(
    *,
    run_id: str,
    issue_code: Optional[str],
    limit: int,
    offset: int,
    db: Session,
) -> AgentRunReliabilityIssuePage:
    run = agent_runs_repository.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    rows = agent_metrics_repository.list_reliability_issues(
        db,
        run_id=run_id,
        issue_code=issue_code,
        limit=limit,
        offset=offset,
    )
    total_count = agent_metrics_repository.count_reliability_issues_filtered(
        db,
        run_id=run_id,
        issue_code=issue_code,
    )
    items = [AgentRunReliabilityIssueRead.model_validate(r.__dict__) for r in rows]
    return AgentRunReliabilityIssuePage(
        run_id=run_id,
        issues=items,
        next_offset=offset + len(items),
        total_count=total_count,
    )


def get_metrics_summary(
    *,
    agent_system: Optional[str],
    agent_name: Optional[str],
    model_name: Optional[str],
    created_from: Optional[datetime],
    created_to: Optional[datetime],
    limit: int,
    offset: int,
    db: Session,
) -> AgentRunMetricsSummary:
    rows = agent_metrics_repository.list_run_metrics(
        db,
        agent_system=agent_system,
        agent_name=agent_name,
        model_name=model_name,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )
    total_runs = len(rows)
    if total_runs == 0:
        return AgentRunMetricsSummary(
            total_runs=0,
            successful_runs=0,
            success_rate=0.0,
            schema_valid_rate=None,
            tool_error_rate=0.0,
            reliability_failure_rate=0.0,
            finalization_failure_rate=0.0,
            runs_with_reliability_issues=0,
            timeout_or_stuck_rate=0.0,
            p50_duration_ms=None,
            p95_duration_ms=None,
            p50_llm_call_count=None,
            p95_llm_call_count=None,
            p50_tokens_total=None,
            p95_tokens_total=None,
            cost_per_successful_run=None,
        )

    successful_runs = sum(1 for r in rows if r.status == "succeeded")
    schema_known = [r.schema_valid for r in rows if r.schema_valid is not None]
    schema_valid_rate = (
        sum(1 for v in schema_known if v) / len(schema_known)
        if schema_known
        else None
    )

    total_tool_calls = sum(int(r.tool_call_count or 0) for r in rows)
    total_tool_errors = sum(int(r.tool_error_count or 0) for r in rows)
    tool_error_rate = (
        (total_tool_errors / total_tool_calls) if total_tool_calls > 0 else 0.0
    )
    runs_with_reliability_issues = sum(1 for r in rows if int(r.reliability_issue_count or 0) > 0)
    runs_with_finalization_failures = sum(1 for r in rows if int(r.finalization_failure_count or 0) > 0)
    timeout_runs = sum(1 for r in rows if (r.failure_reason or "") == FailureCategory.TIMEOUT_ERROR.value)

    durations = [float(r.duration_ms) for r in rows if r.duration_ms is not None]
    llm_counts = [float(r.llm_call_count) for r in rows]
    token_totals = [float(r.tokens_total) for r in rows]
    success_costs = [r.cost_usd_total for r in rows if r.status == "succeeded" and r.cost_usd_total is not None]
    cost_per_success = (sum(success_costs) / len(success_costs)) if success_costs else None

    return AgentRunMetricsSummary(
        total_runs=total_runs,
        successful_runs=successful_runs,
        success_rate=successful_runs / total_runs,
        schema_valid_rate=schema_valid_rate,
        tool_error_rate=tool_error_rate,
        reliability_failure_rate=runs_with_reliability_issues / total_runs,
        finalization_failure_rate=runs_with_finalization_failures / total_runs,
        runs_with_reliability_issues=runs_with_reliability_issues,
        timeout_or_stuck_rate=timeout_runs / total_runs,
        p50_duration_ms=_percentile(durations, 50),
        p95_duration_ms=_percentile(durations, 95),
        p50_llm_call_count=_percentile(llm_counts, 50),
        p95_llm_call_count=_percentile(llm_counts, 95),
        p50_tokens_total=_percentile(token_totals, 50),
        p95_tokens_total=_percentile(token_totals, 95),
        cost_per_successful_run=cost_per_success,
    )


def list_agent_events(
    run_id: str,
    after_seq: int,
    limit: int,
    db: Session,
) -> AgentEventsPage:
    run = agent_runs_repository.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    events = agent_runs_repository.list_events_after(
        db,
        run_id=run_id,
        after_seq=after_seq,
        limit=limit,
    )
    items = [AgentEventRead.model_validate(e.__dict__) for e in events]
    next_after_seq = items[-1].seq if items else after_seq
    return AgentEventsPage(run_id=run_id, events=items, next_after_seq=next_after_seq)


def stream_agent_events(
    run_id: str,
    request: Request,
    after_seq: int,
    poll_interval_s: float,
    db: Session,
) -> StreamingResponse:
    run = agent_runs_repository.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    last_event_id = request.headers.get("Last-Event-ID")
    if last_event_id:
        try:
            after_seq = max(after_seq, int(last_event_id))
        except ValueError:
            pass

    def _event_stream():
        nonlocal after_seq
        last_heartbeat = datetime.utcnow()

        yield "retry: 1000\n\n"

        while True:
            agent_runs_repository.rollback(db)

            events = agent_runs_repository.list_events_after(
                db,
                run_id=run_id,
                after_seq=after_seq,
                limit=200,
            )
            if events:
                for ev in events:
                    item = AgentEventRead.model_validate(ev.__dict__).model_dump(mode="json")
                    after_seq = max(after_seq, item["seq"])
                    yield f"id: {item['seq']}\nevent: agent_event\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"

            run_row = agent_runs_repository.get_run(db, run_id)
            is_terminal = run_row is not None and run_row.status in {"succeeded", "failed", "canceled"}
            if is_terminal and not events:
                yield "event: done\ndata: {}\n\n"
                return

            now = datetime.utcnow()
            if (now - last_heartbeat).total_seconds() >= 10:
                yield ": keep-alive\n\n"
                last_heartbeat = now

            sleep(poll_interval_s)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(_event_stream(), media_type="text/event-stream", headers=headers)


def execute_agent_run(run_id: str, db: Session) -> dict:
    run = agent_runs_repository.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    if run.status in {"running"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Run is already running")
    if run.status in {"succeeded"}:
        return {"run_id": run.id, "status": run.status, "output": run.output_json}

    now = datetime.utcnow()
    run.status = "running"
    run.started_at = now
    run.updated_at = now
    agent_runs_repository.save_run(db, run)

    execute_agent_run_and_persist(db, run)
    if run.status == "succeeded":
        return {"run_id": run.id, "status": run.status, "output": run.output_json}

    raise HTTPException(status_code=500, detail=run.error_text or "Agent run failed")


def list_agent_runs(
    *,
    agent_name: Optional[str],
    status: Optional[RunStatus],
    limit: int,
    offset: int,
    order: str,
    db: Session,
) -> list[AgentRunRead]:
    runs = agent_runs_repository.list_runs(
        db,
        agent_name=agent_name,
        status=status,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [_build_run_read(r, db) for r in runs]
