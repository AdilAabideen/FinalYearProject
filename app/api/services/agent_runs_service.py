from __future__ import annotations

import json
import uuid
from datetime import datetime
from time import sleep
from typing import Any, Optional, Tuple

from fastapi import BackgroundTasks, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agentic.model_registry import get_chat_model, validate_model_for_agent
from app.agentic.agents.agents import get_agent_spec, supported_agent_names
from app.agentic.runtime import AgentRuntime
from app.config import settings
from app.database import SessionLocal
from app.models.agent_run import AgentRun
from app.schemas.agent_runs import (
    AgentEventsPage,
    AgentEventRead,
    AgentRunCreateRequest,
    AgentRunCreateResponse,
    AgentRunRead,
    RunStatus,
)
from app.api.repository import agent_runs_repository

MAX_EVENT_TEXT_LEN = 50_000


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

    try:
        seq, output_json = _run_agent_and_persist(db, run, seq)

        now = datetime.utcnow()
        run.status = "succeeded"
        run.output_json = output_json
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
        return None


def _run_agent_and_persist(db: Session, run: AgentRun, seq: int) -> Tuple[int, Optional[dict]]:
    try:
        spec = get_agent_spec(run.agent_name)
    except KeyError as e:
        raise RuntimeError(f"Unsupported agent_name '{run.agent_name}'") from e

    model_id = run.model_name or settings.OPENAI_MODEL
    model_spec = validate_model_for_agent(
        model_id=model_id,
        agent_name=run.agent_name,
        requires_tools=bool(spec.tools),
        requires_structured_output=spec.output_model is not None,
    )
    validated_input = spec.input_model.model_validate(run.input_json)
    runtime = AgentRuntime(
        model_id=model_id,
        model_spec=model_spec,
        model=get_chat_model(model_id),
    )
    agent = spec.build(runtime)
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

    supports_callbacks = all(
        hasattr(agent, attr) for attr in ("set_event_context", "set_event_handlers")
    )
    if supports_callbacks:
        agent.set_event_context(run_id=run.id, agent_name=run.agent_name, start_seq=seq)
        agent.set_event_handlers([_persist_callback_event])
        output = agent.invoke(payload)
        output_json = _coerce_output_json(output)
        seq = agent_runs_repository.get_last_event_seq(db, run.id)
        return seq, output_json

    # output_json: Optional[dict] = None

    # # Legacy fallback for agent implementations that do not expose callback handlers.
    # for mode, data in agent.stream(payload, stream_mode=["updates", "values"]):
    #     if mode != "updates" or not isinstance(data, dict):
    #         continue

    #     for node_name, node_update in data.items():
    #         if not isinstance(node_update, dict):
    #             continue
    #         messages = node_update.get("messages")
    #         if not isinstance(messages, list):
    #             continue

    #         for msg in messages:
    #             tool_calls = getattr(msg, "tool_calls", None) or []
    #             if tool_calls:
    #                 for tc in tool_calls:
    #                     if not isinstance(tc, dict):
    #                         continue
    #                     seq += 1
    #                     _append_event(
    #                         db=db,
    #                         run=run,
    #                         seq=seq,
    #                         event_type="tool_call",
    #                         node_name=node_name,
    #                         tool_name=tc.get("name"),
    #                         tool_call_id=tc.get("id"),
    #                         payload_json={"args": tc.get("args")},
    #                     )

    #             tool_name = getattr(msg, "name", None)
    #             tool_call_id = getattr(msg, "tool_call_id", None)
    #             tool_status = getattr(msg, "status", None)
    #             content = (getattr(msg, "content", "") or "").strip()

    #             if tool_name and tool_call_id:
    #                 seq += 1
    #                 parsed, raw = _try_parse_json(content)
    #                 _append_event(
    #                     db=db,
    #                     run=run,
    #                     seq=seq,
    #                     event_type="tool_result",
    #                     node_name=node_name,
    #                     tool_name=tool_name,
    #                     tool_call_id=tool_call_id,
    #                     status=tool_status,
    #                     payload_json={"result": parsed} if parsed is not None else None,
    #                     payload_text=raw,
    #                 )

    #             if content and not tool_name:
    #                 parsed, raw = _try_parse_json(content)
    #                 seq += 1
    #                 _append_event(
    #                     db=db,
    #                     run=run,
    #                     seq=seq,
    #                     event_type="assistant",
    #                     node_name=node_name,
    #                     payload_json=parsed,
    #                     payload_text=raw,
    #                 )
    #                 if parsed is not None:
    #                     output_json = parsed

    # return seq, output_json


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
            requires_structured_output=spec.output_model is not None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = AgentRun(
        id=run_id,
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
            requires_structured_output=spec.output_model is not None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = AgentRun(
        id=run_id,
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
    return AgentRunRead.model_validate(run.__dict__)


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
    return [AgentRunRead.model_validate(r.__dict__) for r in runs]
