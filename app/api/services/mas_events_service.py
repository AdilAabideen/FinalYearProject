from __future__ import annotations

import json
from datetime import datetime
from time import sleep

from fastapi import HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.repository import mas_events_repository, mas_runs_repository
from app.schemas.mas_events import MASEventEnvelope, MASEventsPage


_LEGACY_EVENT_TYPE_MAP = {
    "mas_started": "swarm_started",
    "mas_completed": "swarm_completed",
    "mas_failed": "swarm_failed",
}


def _is_legacy_swarm_path(request: Request) -> bool:
    return "/swarm-runs/" in str(request.url.path)


def _serialize_event_envelope(*, event_row, legacy: bool) -> dict:
    item = MASEventEnvelope.model_validate(event_row, from_attributes=True).model_dump(mode="json")
    item["swarm_run_id"] = item.get("mas_run_id")
    item["mas_event_type"] = item.get("event_type")
    if legacy:
        item["event_type"] = _LEGACY_EVENT_TYPE_MAP.get(item["event_type"], item["event_type"])
    return item


def list_mas_events(
    mas_run_id: str,
    after_seq: int,
    limit: int,
    db: Session,
) -> MASEventsPage:
    row = mas_runs_repository.get_mas_run(db, mas_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MAS run not found")

    events = mas_events_repository.list_events_after(
        db,
        mas_run_id=mas_run_id,
        after_seq=after_seq,
        limit=limit,
    )
    items = []
    for event_row in events:
        payload = _serialize_event_envelope(event_row=event_row, legacy=True)
        items.append(MASEventEnvelope.model_validate(payload))
    next_after_seq = items[-1].seq if items else after_seq
    return MASEventsPage(mas_run_id=mas_run_id, events=items, next_after_seq=next_after_seq)


def stream_mas_events(
    mas_run_id: str,
    request: Request,
    after_seq: int,
    poll_interval_s: float,
    db: Session,
) -> StreamingResponse:
    row = mas_runs_repository.get_mas_run(db, mas_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MAS run not found")
    legacy = _is_legacy_swarm_path(request)
    event_name = "swarm_event"

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
            mas_events_repository.rollback(db)

            events = mas_events_repository.list_events_after(
                db,
                mas_run_id=mas_run_id,
                after_seq=after_seq,
                limit=200,
            )
            if events:
                for ev in events:
                    item = _serialize_event_envelope(event_row=ev, legacy=legacy)
                    after_seq = max(after_seq, item["seq"])
                    yield f"id: {item['seq']}\nevent: {event_name}\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"

            run_row = mas_runs_repository.get_mas_run(db, mas_run_id)
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
