from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent_event import AgentEvent
from app.models.agent_llm_call import AgentLLMCall
from app.models.agent_run_metrics import AgentRunMetrics
from app.models.agent_tool_call import AgentToolCall


def append_llm_call(
    db: Session,
    *,
    run_id: str,
    call_index: int,
    agent_system: str,
    agent_name: str,
    model_name: Optional[str],
    call_kind: str,
    iteration: Optional[int],
    started_at: datetime,
    ended_at: datetime,
    latency_ms: int,
    input_tokens: int,
    output_tokens: int,
    tokens_total: int,
    usage_source: str,
    cost_usd: Optional[float],
    had_tool_calls: Optional[bool],
    tool_call_count: Optional[int],
    tool_names: Optional[list[str]],
    error_text: Optional[str] = None,
) -> None:
    row = AgentLLMCall(
        run_id=run_id,
        call_index=call_index,
        agent_system=agent_system,
        agent_name=agent_name,
        model_name=model_name,
        call_kind=call_kind,
        iteration=iteration,
        started_at=started_at,
        ended_at=ended_at,
        latency_ms=latency_ms,
        input_tokens=max(0, int(input_tokens)),
        output_tokens=max(0, int(output_tokens)),
        tokens_total=max(0, int(tokens_total)),
        usage_source=usage_source,
        cost_usd=cost_usd,
        had_tool_calls=had_tool_calls,
        tool_call_count=(max(0, int(tool_call_count)) if tool_call_count is not None else None),
        tool_names_json=tool_names,
        error_text=error_text,
    )
    db.add(row)
    db.commit()


def append_tool_call(
    db: Session,
    *,
    run_id: str,
    agent_name: str,
    iteration: int,
    tool_call_id: Optional[str],
    tool_name: str,
    started_at: datetime,
    ended_at: datetime,
    latency_ms: int,
    status: str,
    result_char_count: int,
    result_estimated_tokens: int,
    error_text: Optional[str] = None,
) -> None:
    row = AgentToolCall(
        run_id=run_id,
        agent_name=agent_name,
        iteration=max(0, int(iteration)),
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        started_at=started_at,
        ended_at=ended_at,
        latency_ms=max(0, int(latency_ms)),
        status=status,
        result_char_count=max(0, int(result_char_count)),
        result_estimated_tokens=max(0, int(result_estimated_tokens)),
        error_text=error_text,
    )
    db.add(row)
    db.commit()


def upsert_run_metrics(
    db: Session,
    *,
    run_id: str,
    agent_system: str,
    agent_name: str,
    model_name: Optional[str],
    status: str,
    failure_reason: Optional[str],
    duration_ms: Optional[int],
    llm_call_count: int,
    tool_call_count: int,
    tool_error_count: int,
    input_tokens_total: int,
    output_tokens_total: int,
    tokens_total: int,
    cost_usd_total: Optional[float],
    schema_valid: Optional[bool],
) -> None:
    row = db.get(AgentRunMetrics, run_id)
    if row is None:
        row = AgentRunMetrics(
            run_id=run_id,
            agent_system=agent_system,
            agent_name=agent_name,
            model_name=model_name,
            status=status,
            failure_reason=failure_reason,
            duration_ms=duration_ms,
            llm_call_count=max(0, int(llm_call_count)),
            tool_call_count=max(0, int(tool_call_count)),
            tool_error_count=max(0, int(tool_error_count)),
            input_tokens_total=max(0, int(input_tokens_total)),
            output_tokens_total=max(0, int(output_tokens_total)),
            tokens_total=max(0, int(tokens_total)),
            cost_usd_total=cost_usd_total,
            schema_valid=schema_valid,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(row)
    else:
        row.agent_system = agent_system
        row.agent_name = agent_name
        row.model_name = model_name
        row.status = status
        row.failure_reason = failure_reason
        row.duration_ms = duration_ms
        row.llm_call_count = max(0, int(llm_call_count))
        row.tool_call_count = max(0, int(tool_call_count))
        row.tool_error_count = max(0, int(tool_error_count))
        row.input_tokens_total = max(0, int(input_tokens_total))
        row.output_tokens_total = max(0, int(output_tokens_total))
        row.tokens_total = max(0, int(tokens_total))
        row.cost_usd_total = cost_usd_total
        row.schema_valid = schema_valid
        row.updated_at = datetime.utcnow()
    db.commit()


def get_run_metrics(db: Session, run_id: str) -> Optional[AgentRunMetrics]:
    return db.get(AgentRunMetrics, run_id)


def list_llm_calls(db: Session, run_id: str) -> list[AgentLLMCall]:
    stmt = (
        select(AgentLLMCall)
        .where(AgentLLMCall.run_id == run_id)
        .order_by(AgentLLMCall.call_index.asc(), AgentLLMCall.id.asc())
    )
    return db.execute(stmt).scalars().all()


def list_tool_calls(db: Session, run_id: str) -> list[AgentToolCall]:
    stmt = (
        select(AgentToolCall)
        .where(AgentToolCall.run_id == run_id)
        .order_by(AgentToolCall.iteration.asc(), AgentToolCall.id.asc())
    )
    return db.execute(stmt).scalars().all()


def list_run_metrics(
    db: Session,
    *,
    agent_system: Optional[str],
    agent_name: Optional[str],
    model_name: Optional[str],
    created_from: Optional[datetime],
    created_to: Optional[datetime],
    limit: int,
    offset: int,
) -> list[AgentRunMetrics]:
    stmt = select(AgentRunMetrics)
    if agent_system:
        stmt = stmt.where(AgentRunMetrics.agent_system == agent_system)
    if agent_name:
        stmt = stmt.where(AgentRunMetrics.agent_name == agent_name)
    if model_name:
        stmt = stmt.where(AgentRunMetrics.model_name == model_name)
    if created_from:
        stmt = stmt.where(AgentRunMetrics.created_at >= created_from)
    if created_to:
        stmt = stmt.where(AgentRunMetrics.created_at <= created_to)
    stmt = (
        stmt.order_by(AgentRunMetrics.created_at.desc(), AgentRunMetrics.run_id.desc())
        .offset(offset)
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def count_tool_events(db: Session, run_id: str) -> tuple[int, int]:
    tool_calls_stmt = (
        select(func.count())
        .select_from(AgentEvent)
        .where(AgentEvent.run_id == run_id, AgentEvent.event_type == "tool_call")
    )
    tool_errors_stmt = (
        select(func.count())
        .select_from(AgentEvent)
        .where(
            AgentEvent.run_id == run_id,
            AgentEvent.event_type == "tool_result",
            AgentEvent.status == "error",
        )
    )
    tool_call_count = int(db.execute(tool_calls_stmt).scalar_one() or 0)
    tool_error_count = int(db.execute(tool_errors_stmt).scalar_one() or 0)
    return tool_call_count, tool_error_count
