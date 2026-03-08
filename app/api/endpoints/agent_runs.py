from __future__ import annotations

import json
import uuid
from datetime import datetime
from time import sleep
from typing import Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.models.agent_event import AgentEvent
from app.models.agent_run import AgentRun
from app.schemas.agent_runs import (
    AgentEventsPage,
    AgentEventRead,
    AgentRunCreateRequest,
    AgentRunCreateResponse,
    AgentRunRead,
    RunStatus,
)
from app.agentic.registry import get_agent_spec, supported_agent_names

router = APIRouter()

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
    ev = AgentEvent(
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
    db.add(ev)
    db.commit()


def _get_last_seq(db: Session, run_id: str) -> int:
    stmt = (
        select(AgentEvent.seq)
        .where(AgentEvent.run_id == run_id)
        .order_by(AgentEvent.seq.desc())
        .limit(1)
    )
    last = db.execute(stmt).scalar_one_or_none()
    return int(last) if last is not None else 0


def _ensure_run_start_event(db: Session, run: AgentRun) -> int:
    """
    Ensure a run has a `run_start` event (seq=1) before executing.

    Returns the current last seq (>= 1 once started).
    """
    seq = _get_last_seq(db, run.id)
    if seq > 0:
        return seq

    now = datetime.utcnow()
    if run.status != "running":
        run.status = "running"
    if run.started_at is None:
        run.started_at = now
    run.updated_at = now
    db.add(run)
    db.commit()

    _append_event(
        db=db,
        run=run,
        seq=1,
        event_type="run_start",
        payload_json={"input": run.input_json},
    )
    return 1


def _execute_agent_run_and_persist(db: Session, run: AgentRun) -> Optional[dict]:
    """
    Execute the agent run, persist all events and terminal status, and never raise.

    This is the shared execution path used by:
    - background execution (`/agent-runs/start`)
    - synchronous execution (`/agent-runs/{id}/execute`)
    - test harness execution (`/tests/.../stream`)
    """
    seq = _ensure_run_start_event(db, run)

    try:
        seq, output_json = _run_agent_and_persist(db, run, seq)

        now = datetime.utcnow()
        run.status = "succeeded"
        run.output_json = output_json
        run.finished_at = now
        run.updated_at = now
        db.add(run)
        db.commit()

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
        db.add(run)
        db.commit()

        seq = _get_last_seq(db, run.id)
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
    validated_input = spec.input_model.model_validate(run.input_json)
    agent = spec.build()
    payload = {"messages": [("user", validated_input.model_dump_json())]}

    output_json: Optional[dict] = None

    for mode, data in agent.stream(payload, stream_mode=["updates", "values"]):
        if mode != "updates" or not isinstance(data, dict):
            continue

        for node_name, node_update in data.items():
            if not isinstance(node_update, dict):
                continue
            messages = node_update.get("messages")
            if not isinstance(messages, list):
                continue

            for msg in messages:
                tool_calls = getattr(msg, "tool_calls", None) or []
                if tool_calls:
                    for tc in tool_calls:
                        if not isinstance(tc, dict):
                            continue
                        seq += 1
                        _append_event(
                            db=db,
                            run=run,
                            seq=seq,
                            event_type="tool_call",
                            node_name=node_name,
                            tool_name=tc.get("name"),
                            tool_call_id=tc.get("id"),
                            payload_json={"args": tc.get("args")},
                        )

                tool_name = getattr(msg, "name", None)
                tool_call_id = getattr(msg, "tool_call_id", None)
                tool_status = getattr(msg, "status", None)
                content = (getattr(msg, "content", "") or "").strip()

                if tool_name and tool_call_id:
                    seq += 1
                    parsed, raw = _try_parse_json(content)
                    event_type = "thought" if tool_name == "log_thought" else "tool_result"
                    _append_event(
                        db=db,
                        run=run,
                        seq=seq,
                        event_type=event_type,
                        node_name=node_name,
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        status=tool_status,
                        payload_json={"result": parsed} if parsed is not None else None,
                        payload_text=raw,
                    )

                if content and not tool_name:
                    parsed, raw = _try_parse_json(content)
                    seq += 1
                    _append_event(
                        db=db,
                        run=run,
                        seq=seq,
                        event_type="assistant",
                        node_name=node_name,
                        payload_json=parsed,
                        payload_text=raw,
                    )
                    if parsed is not None:
                        output_json = parsed

    return seq, output_json


def _execute_run_in_background(run_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(AgentRun, run_id)
        if run is None:
            return
        if run.status != "running":
            return

        _execute_agent_run_and_persist(db, run)
    finally:
        db.close()


@router.post("", response_model=AgentRunCreateResponse)
def create_agent_run(payload: AgentRunCreateRequest, db: Session = Depends(get_db)):
    supported = supported_agent_names()
    if payload.agent_name not in supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported agent_name '{payload.agent_name}'. Supported: {sorted(supported)}",
        )

    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = AgentRun(
        id=run_id,
        agent_name=payload.agent_name,
        status="created",
        model_name=settings.OPENAI_MODEL,
        input_json=payload.input,
        started_at=None,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(run)
    db.commit()

    return AgentRunCreateResponse(run_id=run_id, status="created")


@router.post("/start", response_model=AgentRunCreateResponse)
def start_agent_run(
    payload: AgentRunCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    supported = supported_agent_names()
    if payload.agent_name not in supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported agent_name '{payload.agent_name}'. Supported: {sorted(supported)}",
        )

    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = AgentRun(
        id=run_id,
        agent_name=payload.agent_name,
        status="running",
        model_name=settings.OPENAI_MODEL,
        input_json=payload.input,
        started_at=now,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(run)
    db.commit()

    _append_event(
        db=db,
        run=run,
        seq=1,
        event_type="run_start",
        payload_json={"input": run.input_json},
    )

    background_tasks.add_task(_execute_run_in_background, run_id)
    return AgentRunCreateResponse(run_id=run_id, status="running")


@router.get("/{run_id}", response_model=AgentRunRead)
def get_agent_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return AgentRunRead.model_validate(run.__dict__)


@router.get("/{run_id}/events", response_model=AgentEventsPage)
def list_agent_events(
    run_id: str,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    stmt = (
        select(AgentEvent)
        .where(AgentEvent.run_id == run_id, AgentEvent.seq > after_seq)
        .order_by(AgentEvent.seq.asc())
        .limit(limit)
    )
    events = db.execute(stmt).scalars().all()
    items = [AgentEventRead.model_validate(e.__dict__) for e in events]
    next_after_seq = items[-1].seq if items else after_seq
    return AgentEventsPage(run_id=run_id, events=items, next_after_seq=next_after_seq)


@router.get("/{run_id}/events/stream")
def stream_agent_events(
    run_id: str,
    request: Request,
    after_seq: int = Query(default=0, ge=0),
    poll_interval_s: float = Query(default=0.25, ge=0.05, le=5.0),
    db: Session = Depends(get_db),
):
    run = db.get(AgentRun, run_id)
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
            db.rollback()

            stmt = (
                select(AgentEvent)
                .where(AgentEvent.run_id == run_id, AgentEvent.seq > after_seq)
                .order_by(AgentEvent.seq.asc())
                .limit(200)
            )
            events = db.execute(stmt).scalars().all()
            if events:
                for ev in events:
                    item = AgentEventRead.model_validate(ev.__dict__).model_dump(mode="json")
                    after_seq = max(after_seq, item["seq"])
                    yield f"id: {item['seq']}\nevent: agent_event\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"

            run_row = db.get(AgentRun, run_id)
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


@router.post("/{run_id}/execute")
def execute_agent_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
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
    db.add(run)
    db.commit()

    _execute_agent_run_and_persist(db, run)
    if run.status == "succeeded":
        return {"run_id": run.id, "status": run.status, "output": run.output_json}
    raise HTTPException(status_code=500, detail=run.error_text or "Agent run failed")


@router.get("", response_model=list[AgentRunRead])
def list_agent_runs(
    agent_name: Optional[str] = Query(
        default=None, description="Optional filter (e.g. 'vitals_agent')."
    ),
    status: Optional[RunStatus] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    stmt = select(AgentRun)

    if agent_name:
        stmt = stmt.where(AgentRun.agent_name == agent_name)
    if status:
        stmt = stmt.where(AgentRun.status == status)

    if order == "asc":
        stmt = stmt.order_by(AgentRun.created_at.asc(), AgentRun.id.asc())
    else:
        stmt = stmt.order_by(AgentRun.created_at.desc(), AgentRun.id.desc())

    stmt = stmt.offset(offset).limit(limit)

    runs = db.execute(stmt).scalars().all()
    return [AgentRunRead.model_validate(r.__dict__) for r in runs]
