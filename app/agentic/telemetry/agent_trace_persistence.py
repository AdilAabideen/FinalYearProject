from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.api.repository import agent_metrics_repository, agent_runs_repository
from app.agentic.agents.agents import get_agent_spec
from app.agentic.runtime.failure_taxonomy import FailureCategory
from app.models.agent_run import AgentRun

MAX_EVENT_TEXT_LEN = 50_000


def wire_agent_trace_persistence(
    *,
    agent: Any,
    session_factory: Callable[[], Session],
    run_id: str,
    agent_name: str,
    agent_system: str,
    model_name: str | None,
    model_spec: Any,
    start_seq: int = 0,
) -> None:
    supports_callbacks = all(hasattr(agent, attr) for attr in ("set_event_context", "set_event_handlers"))
    if not supports_callbacks:
        raise RuntimeError("Agent does not support callback event persistence")

    def _persist_callback_event(item: dict[str, Any]) -> None:
        db = session_factory()
        try:
            agent_runs_repository.append_event(
                db,
                run_id=run_id,
                agent_name=agent_name,
                seq=int(item.get("seq") or 0),
                event_type=str(item.get("event_type") or ""),
                node_name=_string_or_none(item.get("node_name")),
                tool_name=_string_or_none(item.get("tool_name")),
                tool_call_id=_string_or_none(item.get("tool_call_id")),
                status=_string_or_none(item.get("status")),
                payload_json=_normalize_payload_json(item.get("payload_json")),
                payload_text=_safe_text(item.get("payload_text")) if item.get("payload_text") else None,
                created_at=item.get("created_at") or datetime.utcnow(),
            )
        finally:
            db.close()

    def _persist_llm_call(item: dict[str, Any]) -> None:
        input_tokens = int(item.get("input_tokens") or 0)
        output_tokens = int(item.get("output_tokens") or 0)
        total_tokens = int(item.get("tokens_total") or (input_tokens + output_tokens))
        cost_usd = _cost_from_tokens(
            model_spec=model_spec,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        db = session_factory()
        try:
            agent_metrics_repository.append_llm_call(
                db,
                run_id=run_id,
                call_index=int(item.get("call_index") or 0),
                agent_system=agent_system,
                agent_name=agent_name,
                model_name=_string_or_none(item.get("model_name")) or model_name,
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
                error_text=_string_or_none(item.get("error_text")),
            )
        finally:
            db.close()

    def _persist_tool_call(item: dict[str, Any]) -> None:
        db = session_factory()
        try:
            agent_metrics_repository.append_tool_call(
                db,
                run_id=run_id,
                agent_name=agent_name,
                iteration=int(item.get("iteration") or 0),
                tool_call_id=_string_or_none(item.get("tool_call_id")),
                tool_name=str(item.get("tool_name") or "tool"),
                started_at=item.get("started_at") or datetime.utcnow(),
                ended_at=item.get("ended_at") or datetime.utcnow(),
                latency_ms=int(item.get("latency_ms") or 0),
                status=str(item.get("status") or "error"),
                result_char_count=int(item.get("result_char_count") or 0),
                result_estimated_tokens=int(item.get("result_estimated_tokens") or 0),
                error_text=_string_or_none(item.get("error_text")),
            )
        finally:
            db.close()

    agent.set_event_context(run_id=run_id, agent_name=agent_name, start_seq=start_seq)
    agent.set_event_handlers([_persist_callback_event])
    if hasattr(agent, "set_llm_call_handlers"):
        agent.set_llm_call_handlers([_persist_llm_call])
    if hasattr(agent, "set_tool_call_handlers"):
        agent.set_tool_call_handlers([_persist_tool_call])


def _safe_text(text: str) -> str:
    raw = str(text)
    if len(raw) <= MAX_EVENT_TEXT_LEN:
        return raw
    return raw[:MAX_EVENT_TEXT_LEN] + "…(truncated)"


def _normalize_payload_json(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    return {"value": raw}


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


def _cost_from_tokens(
    *,
    model_spec: Any,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
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


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def persist_agent_run_metrics(
    *,
    session_factory: Callable[[], Session],
    run_id: str,
    agent_system: str,
) -> None:
    db = session_factory()
    try:
        run = agent_runs_repository.get_run(db, run_id)
        if run is None:
            return
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

        duration_ms: int | None = None
        if run.started_at and run.finished_at:
            duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

        failure_reason: str | None = None
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
    finally:
        db.close()


def _schema_valid_for_run(run: AgentRun) -> bool | None:
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
