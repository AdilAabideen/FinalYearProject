from __future__ import annotations

import json
from datetime import datetime
from time import sleep

from fastapi import HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.repository import swarm_events_repository, swarm_runs_repository
from app.schemas.swarm_events import SwarmEventEnvelope, SwarmEventsPage


def list_swarm_events(
    swarm_run_id: str,
    after_seq: int,
    limit: int,
    db: Session,
) -> SwarmEventsPage:
    row = swarm_runs_repository.get_swarm_run(db, swarm_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swarm run not found")

    events = swarm_events_repository.list_events_after(
        db,
        swarm_run_id=swarm_run_id,
        after_seq=after_seq,
        limit=limit,
    )
    items = [SwarmEventEnvelope.model_validate(e, from_attributes=True) for e in events]
    next_after_seq = items[-1].seq if items else after_seq
    return SwarmEventsPage(swarm_run_id=swarm_run_id, events=items, next_after_seq=next_after_seq)


def stream_swarm_events(
    swarm_run_id: str,
    request: Request,
    after_seq: int,
    poll_interval_s: float,
    db: Session,
) -> StreamingResponse:
    row = swarm_runs_repository.get_swarm_run(db, swarm_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swarm run not found")

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
            swarm_events_repository.rollback(db)

            events = swarm_events_repository.list_events_after(
                db,
                swarm_run_id=swarm_run_id,
                after_seq=after_seq,
                limit=200,
            )
            if events:
                for ev in events:
                    item = SwarmEventEnvelope.model_validate(ev, from_attributes=True).model_dump(mode="json")
                    after_seq = max(after_seq, item["seq"])
                    yield f"id: {item['seq']}\nevent: swarm_event\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"

            run_row = swarm_runs_repository.get_swarm_run(db, swarm_run_id)
            is_terminal = run_row is not None and run_row.status in {"completed", "failed", "canceled"}
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
