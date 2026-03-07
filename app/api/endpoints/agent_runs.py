from __future__ import annotations

import json
import uuid
from datetime import datetime
from time import sleep

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.agent_event import AgentEvent
from app.models.agent_run import AgentRun
from app.schemas.agent_runs import (
    AgentEventsPage,
    AgentEventRead,
    AgentRunCreateRequest,
    AgentRunCreateResponse,
    AgentRunRead,
)

router = APIRouter()

SUPPORTED_AGENTS = {"vitals_agent"}

MAX_EVENT_TEXT_LEN = 50_000


def _safe_text(text: str) -> str:
    if len(text) <= MAX_EVENT_TEXT_LEN:
        return text
    return text[:MAX_EVENT_TEXT_LEN] + "…(truncated)"


def _try_parse_json(text: str) -> tuple[dict | None, str | None]:
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
    node_name: str | None = None,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    status: str | None = None,
    payload_json: dict | None = None,
    payload_text: str | None = None,
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


@router.post("", response_model=AgentRunCreateResponse)
def create_agent_run(payload: AgentRunCreateRequest, db: Session = Depends(get_db)):
    if payload.agent_name not in SUPPORTED_AGENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported agent_name '{payload.agent_name}'. Supported: {sorted(SUPPORTED_AGENTS)}",
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
    after_seq: int = Query(default=0, ge=0),
    poll_interval_s: float = Query(default=0.25, ge=0.05, le=5.0),
    db: Session = Depends(get_db),
):
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    def _event_stream():
        nonlocal after_seq
        last_heartbeat = datetime.utcnow()

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
                    yield f"event: agent_event\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"

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

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


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

    seq = 1
    _append_event(
        db=db,
        run=run,
        seq=seq,
        event_type="run_start",
        payload_json={"input": run.input_json},
    )

    try:
        if run.agent_name != "vitals_agent":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported agent_name '{run.agent_name}'",
            )

        from app.agentic.agents.vitals_agent import build_vitals_agent
        from app.schemas.vitals_agent import VitalsAgentInput

        vitals_input = VitalsAgentInput.model_validate(run.input_json)
        agent = build_vitals_agent()
        payload = {"messages": [("user", vitals_input.model_dump_json())]}

        output_json: dict | None = None

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

        return {"run_id": run.id, "status": run.status, "output": run.output_json}
    except HTTPException:
        raise
    except Exception as e:
        now = datetime.utcnow()
        run.status = "failed"
        run.error_text = str(e)
        run.finished_at = now
        run.updated_at = now
        db.add(run)
        db.commit()

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

        raise HTTPException(status_code=500, detail=str(e))
