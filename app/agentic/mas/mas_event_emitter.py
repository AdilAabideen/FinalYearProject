from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Callable, Dict, Iterator, Mapping, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.repository import mas_events_repository

MAX_EVENT_TEXT_LEN = 50_000
MAX_EVENT_INSERT_RETRIES = 8


class MASEventEmitter:
    """Persist normalized mas event envelopes for replay and SSE."""

    def __init__(
        self,
        *,
        workflow_id: str,
        db: Session | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self.workflow_id = workflow_id
        self.db = db
        self.session_factory = session_factory

    def emit(
        self,
        *,
        mas_run_id: str,
        event_type: str,
        agent_run_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        handoff_id: Optional[str] = None,
        gate_evaluation_id: Optional[str] = None,
        final_output_id: Optional[str] = None,
        status: Optional[str] = None,
        payload_json: Optional[dict[str, Any]] = None,
        payload_text: Optional[str] = None,
    ) -> int:
        with self._session_scope() as db:
            sanitized_payload = self._sanitize_json(payload_json)
            safe_payload_text = self._safe_text(payload_text)

            for attempt in range(MAX_EVENT_INSERT_RETRIES):
                next_seq = mas_events_repository.get_last_event_seq(db, mas_run_id) + 1
                try:
                    mas_events_repository.append_event(
                        db,
                        mas_run_id=mas_run_id,
                        seq=next_seq,
                        event_type=event_type,
                        workflow_id=self.workflow_id,
                        agent_run_id=agent_run_id,
                        agent_name=agent_name,
                        handoff_id=handoff_id,
                        gate_evaluation_id=gate_evaluation_id,
                        final_output_id=final_output_id,
                        status=status,
                        payload_json=sanitized_payload,
                        payload_text=safe_payload_text,
                    )
                    return next_seq
                except IntegrityError as exc:
                    mas_events_repository.rollback(db)
                    if not self._is_seq_conflict(exc) or attempt == MAX_EVENT_INSERT_RETRIES - 1:
                        raise
                    time.sleep(0.002 * (attempt + 1))

        raise RuntimeError("Failed to persist mas event after retrying sequence allocation.")

    @classmethod
    def _sanitize_json(cls, value: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if value is None:
            return None
        return cls._sanitize_value(value)

    @classmethod
    def _sanitize_value(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Mapping):
            return {str(k): cls._sanitize_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._sanitize_value(v) for v in value]
        if hasattr(value, "model_dump") and callable(value.model_dump):
            try:
                return cls._sanitize_value(value.model_dump(mode="json"))
            except Exception:
                return cls._sanitize_value(value.model_dump())
        try:
            json.dumps(value)
            return value
        except Exception:
            return str(value)

    @staticmethod
    def _safe_text(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value)
        if len(text) <= MAX_EVENT_TEXT_LEN:
            return text
        return text[:MAX_EVENT_TEXT_LEN] + "…(truncated)"

    @staticmethod
    def _is_seq_conflict(exc: IntegrityError) -> bool:
        message = str(exc.orig if getattr(exc, "orig", None) is not None else exc)
        return (
            "mas_events.mas_run_id, mas_events.seq" in message
            or "uq_mas_events_run_seq" in message
        )

    @contextmanager
    def _session_scope(self) -> Iterator[Session]:
        if self.session_factory is not None:
            db = self.session_factory()
            try:
                yield db
            finally:
                db.close()
            return
        if self.db is None:
            raise ValueError("MASEventEmitter requires either db or session_factory.")
        yield self.db
