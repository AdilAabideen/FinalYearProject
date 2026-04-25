from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, Mapping, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.api.repository import (
    agent_runs_repository,
    swarm_final_outputs_repository,
    swarm_gate_evaluations_repository,
    swarm_handoffs_repository,
    swarm_runs_repository,
)
from app.agentic.swarm.swarm_event_emitter import SwarmEventEmitter
from app.agentic.swarm.gate_evaluator import GateEvaluationOutcome
from app.agentic.swarm_contract import AgentExecutionResult, AgentName, HandoffEnvelope, SwarmState
from app.models.agent_run import AgentRun
from app.models.swarm_final_output import SwarmFinalOutput
from app.models.swarm_gate_evaluation import SwarmGateEvaluation
from app.models.swarm_handoff import SwarmHandoff


@dataclass(frozen=True)
class TrackedAgentExecution:
    swarm_run_id: str
    agent_run_id: str
    agent_name: AgentName
    sequence_index: int
    incoming_handoff_id: str | None


@dataclass(frozen=True)
class TrackedExecutionPersistenceOutcome:
    agent_run_id: str
    sequence_index: int
    handoff_id: str | None = None


class SwarmExecutionTracker:
    """Persist MAS execution state alongside the LangGraph runtime.

    This tracker is intentionally explicit rather than callback-driven:
    agent execution, handoff creation, and handoff acceptance are core
    runtime writes, not optional observers.
    """

    def __init__(
        self,
        *,
        db: Session | None = None,
        session_factory: Callable[[], Session] | None = None,
        workflow_id: str,
        workflow_version: str | None = None,
        event_emitter: SwarmEventEmitter | None = None,
    ) -> None:
        self.db = db
        self.session_factory = session_factory
        self.workflow_id = workflow_id
        self.workflow_version = workflow_version
        self.event_emitter = event_emitter

    def begin_agent_execution(
        self,
        *,
        agent_name: AgentName,
        state: SwarmState,
        pending_agent_payload: Dict[str, Any],
    ) -> TrackedAgentExecution | None:
        ctx = self._execution_context(state)
        swarm_run_id = self._string_or_none(ctx.get("swarm_run_id"))
        if swarm_run_id is None:
            return None

        sequence_index = self._next_sequence_index(ctx)
        incoming_handoff_id = self._incoming_handoff_id(agent_name=agent_name, state=state)
        now = self._utcnow()
        run_id = str(uuid4())

        with self._session_scope() as db:
            run = AgentRun(
                id=run_id,
                swarm_run_id=swarm_run_id,
                workflow_id=self._string_or_none(ctx.get("workflow_id")) or self.workflow_id,
                workflow_version=self._string_or_none(ctx.get("workflow_version")) or self.workflow_version,
                sequence_index=sequence_index,
                parent_handoff_id=incoming_handoff_id,
                outgoing_handoff_id=None,
                is_final_agent=False,
                agent_name=agent_name,
                status="running",
                model_name=None,
                input_json=dict(pending_agent_payload),
                output_json=None,
                error_text=None,
                started_at=now,
                finished_at=None,
                created_at=now,
                updated_at=now,
            )
            agent_runs_repository.save_run(db, run)
            self._accept_handoff_if_present(
                db=db,
                incoming_handoff_id=incoming_handoff_id,
                to_agent_run_id=run.id,
                accepted_at=now,
            )
            self._accept_pending_handoffs_for_target(
                db=db,
                swarm_run_id=swarm_run_id,
                target_agent_name=agent_name,
                to_agent_run_id=run.id,
                accepted_at=now,
            )
            self._update_swarm_run_on_agent_start(db=db, swarm_run_id=swarm_run_id, agent_run_id=run.id)
        self._emit_event(
            swarm_run_id=swarm_run_id,
            event_type="agent_started",
            agent_run_id=run_id,
            agent_name=agent_name,
            status="running",
            payload_json={
                "sequence_index": sequence_index,
                "parent_handoff_id": incoming_handoff_id,
            },
        )

        return TrackedAgentExecution(
            swarm_run_id=swarm_run_id,
            agent_run_id=run_id,
            agent_name=agent_name,
            sequence_index=sequence_index,
            incoming_handoff_id=incoming_handoff_id,
        )

    def complete_agent_execution(
        self,
        *,
        tracked: TrackedAgentExecution | None,
        result: AgentExecutionResult,
    ) -> TrackedExecutionPersistenceOutcome | None:
        if tracked is None:
            return None
        now = self._utcnow()
        handoff_id: str | None = None

        with self._session_scope() as db:
            run = agent_runs_repository.get_run(db, tracked.agent_run_id)
            if run is None:
                return None

            run.output_json = self._result_output_json(result)
            run.finished_at = now
            run.updated_at = now

            if result.status == "error":
                run.status = "failed"
                run.error_text = self._error_text(result.output)
                agent_runs_repository.save_run(db, run)
                self._emit_event(
                    swarm_run_id=tracked.swarm_run_id,
                    event_type="agent_completed",
                    agent_run_id=run.id,
                    agent_name=tracked.agent_name,
                    status="failed",
                    payload_json={
                        "sequence_index": tracked.sequence_index,
                        "output": self._result_output_json(result),
                    },
                )
                return TrackedExecutionPersistenceOutcome(
                    agent_run_id=run.id,
                    sequence_index=tracked.sequence_index,
                )

            run.status = "succeeded"
            run.error_text = None

            if result.status == "final":
                run.is_final_agent = True
                final_output_id = self._persist_swarm_final_output(
                    db=db,
                    swarm_run_id=tracked.swarm_run_id,
                    final_agent_run_id=run.id,
                    final_output=dict(result.final_output or {}),
                    created_at=now,
                )
                self._emit_event(
                    swarm_run_id=tracked.swarm_run_id,
                    event_type="final_output_created",
                    agent_run_id=run.id,
                    agent_name=tracked.agent_name,
                    final_output_id=final_output_id,
                    status="completed",
                    payload_json=dict(result.final_output or {}),
                )
            elif result.handoff is not None:
                handoff_id = self._record_handoff_created(
                    db=db,
                    tracked=tracked,
                    handoff=result.handoff,
                    created_at=now,
                )
                run.outgoing_handoff_id = handoff_id

            agent_runs_repository.save_run(db, run)
        self._emit_event(
            swarm_run_id=tracked.swarm_run_id,
            event_type="agent_completed",
            agent_run_id=tracked.agent_run_id,
            agent_name=tracked.agent_name,
            status="succeeded",
            payload_json={
                "sequence_index": tracked.sequence_index,
                "result_status": result.status,
                "handoff_id": handoff_id,
                "output": self._result_output_json(result),
            },
        )
        return TrackedExecutionPersistenceOutcome(
            agent_run_id=tracked.agent_run_id,
            sequence_index=tracked.sequence_index,
            handoff_id=handoff_id,
        )

    def state_updates_for_completion(
        self,
        *,
        tracked: TrackedAgentExecution | None,
        persisted: TrackedExecutionPersistenceOutcome | None,
    ) -> Dict[str, Any]:
        if tracked is None or persisted is None:
            return {}

        execution_context_update: Dict[str, Any] = {
            "current_agent_run_id": persisted.agent_run_id,
            "last_completed_agent_run_id": persisted.agent_run_id,
            "next_sequence_index": int(persisted.sequence_index) + 1,
        }
        if persisted.handoff_id is not None:
            execution_context_update["last_handoff_id"] = persisted.handoff_id

        return {"execution_context": execution_context_update}

    def decorate_handoff_dict(
        self,
        *,
        handoff_dict: Dict[str, Any],
        persisted: TrackedExecutionPersistenceOutcome | None,
    ) -> Dict[str, Any]:
        if persisted is None or persisted.handoff_id is None:
            return dict(handoff_dict)
        decorated = dict(handoff_dict)
        decorated["handoff_id"] = persisted.handoff_id
        return decorated

    def record_gate_evaluation(
        self,
        *,
        gate_id: str,
        state: SwarmState,
        outcome: GateEvaluationOutcome,
    ) -> str | None:
        ctx = self._execution_context(state)
        swarm_run_id = self._string_or_none(ctx.get("swarm_run_id"))
        if swarm_run_id is None:
            return None

        now = self._utcnow()
        evaluation_id = str(uuid4())
        with self._session_scope() as db:
            row = SwarmGateEvaluation(
                id=evaluation_id,
                swarm_run_id=swarm_run_id,
                gate_id=gate_id,
                ready=bool(outcome.ready),
                satisfied_sources_json=list(outcome.satisfied_sources),
                missing_sources_json=list(outcome.missing_sources),
                next_target=outcome.next_target,
                handoffs_to_target_json=list(outcome.handoffs_to_target),
                metadata_json={"terminal": bool(outcome.terminal)},
                created_at=now,
                updated_at=now,
            )
            swarm_gate_evaluations_repository.save_swarm_gate_evaluation(db, row)
            self._update_swarm_run_on_gate_evaluation(
                db=db,
                swarm_run_id=swarm_run_id,
                gate_id=gate_id,
                now=now,
            )
        self._emit_event(
            swarm_run_id=swarm_run_id,
            event_type="gate_evaluated",
            gate_evaluation_id=evaluation_id,
            status="ready" if outcome.ready else "blocked",
            payload_json={
                "gate_id": gate_id,
                "ready": bool(outcome.ready),
                "satisfied_sources": list(outcome.satisfied_sources),
                "missing_sources": list(outcome.missing_sources),
                "next_target": outcome.next_target,
                "handoffs_to_target": list(outcome.handoffs_to_target),
            },
        )
        return evaluation_id

    def _record_handoff_created(
        self,
        *,
        db: Session,
        tracked: TrackedAgentExecution,
        handoff: HandoffEnvelope,
        created_at: datetime,
    ) -> str:
        handoff_id = str(uuid4())
        row = SwarmHandoff(
            id=handoff_id,
            swarm_run_id=tracked.swarm_run_id,
            from_agent_run_id=tracked.agent_run_id,
            from_agent_name=tracked.agent_name,
            to_agent_name=handoff.target_agent,
            to_agent_run_id=None,
            handoff_name=handoff.handoff_name,
            payload_schema=handoff.payload_schema,
            payload_json=dict(handoff.payload or {}),
            status="created",
            accepted_at=None,
            latency_ms=None,
            metadata_json={
                "from_agent": handoff.from_agent,
                "target_agent": handoff.target_agent,
            },
            created_at=created_at,
            updated_at=created_at,
        )
        swarm_handoffs_repository.save_swarm_handoff(db, row)
        self._emit_event(
            swarm_run_id=tracked.swarm_run_id,
            event_type="handoff_created",
            agent_run_id=tracked.agent_run_id,
            agent_name=tracked.agent_name,
            handoff_id=handoff_id,
            status="created",
            payload_json={
                "handoff_name": handoff.handoff_name,
                "from_agent": handoff.from_agent,
                "target_agent": handoff.target_agent,
                "payload_schema": handoff.payload_schema,
                "payload": dict(handoff.payload or {}),
            },
        )
        return handoff_id

    def _accept_handoff_if_present(
        self,
        *,
        db: Session,
        incoming_handoff_id: str | None,
        to_agent_run_id: str,
        accepted_at: datetime,
    ) -> None:
        if incoming_handoff_id is None:
            return

        row = swarm_handoffs_repository.get_swarm_handoff(db, incoming_handoff_id)
        if row is None:
            return

        row.to_agent_run_id = to_agent_run_id
        row.accepted_at = accepted_at
        row.status = "accepted"
        if row.created_at is not None:
            row.latency_ms = max(0, int((accepted_at - row.created_at).total_seconds() * 1000))
        row.updated_at = accepted_at
        swarm_handoffs_repository.save_swarm_handoff(db, row)

    def _accept_pending_handoffs_for_target(
        self,
        *,
        db: Session,
        swarm_run_id: str,
        target_agent_name: str,
        to_agent_run_id: str,
        accepted_at: datetime,
    ) -> None:
        rows = swarm_handoffs_repository.list_pending_handoffs_for_target(
            db,
            swarm_run_id=swarm_run_id,
            to_agent_name=target_agent_name,
        )
        for row in rows:
            if row.to_agent_run_id is not None:
                continue
            row.to_agent_run_id = to_agent_run_id
            row.accepted_at = accepted_at
            row.status = "accepted"
            if row.created_at is not None:
                row.latency_ms = max(0, int((accepted_at - row.created_at).total_seconds() * 1000))
            row.updated_at = accepted_at
            swarm_handoffs_repository.save_swarm_handoff(db, row)

    def _update_swarm_run_on_agent_start(self, *, db: Session, swarm_run_id: str, agent_run_id: str) -> None:
        row = swarm_runs_repository.get_swarm_run(db, swarm_run_id)
        if row is None:
            return
        now = self._utcnow()
        row.current_agent_run_id = agent_run_id
        row.current_gate_id = None
        row.status = "running"
        if row.started_at is None:
            row.started_at = now
        row.updated_at = now
        swarm_runs_repository.save_swarm_run(db, row)

    def _update_swarm_run_on_gate_evaluation(
        self,
        *,
        db: Session,
        swarm_run_id: str,
        gate_id: str,
        now: datetime,
    ) -> None:
        row = swarm_runs_repository.get_swarm_run(db, swarm_run_id)
        if row is None:
            return
        row.current_gate_id = gate_id
        row.updated_at = now
        swarm_runs_repository.save_swarm_run(db, row)

    def _persist_swarm_final_output(
        self,
        *,
        db: Session,
        swarm_run_id: str,
        final_agent_run_id: str,
        final_output: Dict[str, Any],
        created_at: datetime,
    ) -> str:
        final_output_id = str(uuid4())
        row = SwarmFinalOutput(
            id=final_output_id,
            swarm_run_id=swarm_run_id,
            final_agent_run_id=final_agent_run_id,
            workflow_id=self.workflow_id,
            workflow_version=self.workflow_version,
            output_json=dict(final_output),
            metadata_json=None,
            created_at=created_at,
            updated_at=created_at,
        )
        swarm_final_outputs_repository.save_swarm_final_output(db, row)
        return final_output_id

    def _emit_event(
        self,
        *,
        swarm_run_id: str,
        event_type: str,
        agent_run_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        handoff_id: Optional[str] = None,
        gate_evaluation_id: Optional[str] = None,
        final_output_id: Optional[str] = None,
        status: Optional[str] = None,
        payload_json: Optional[dict[str, Any]] = None,
        payload_text: Optional[str] = None,
    ) -> None:
        if self.event_emitter is None:
            return
        self.event_emitter.emit(
            swarm_run_id=swarm_run_id,
            event_type=event_type,
            agent_run_id=agent_run_id,
            agent_name=agent_name,
            handoff_id=handoff_id,
            gate_evaluation_id=gate_evaluation_id,
            final_output_id=final_output_id,
            status=status,
            payload_json=payload_json,
            payload_text=payload_text,
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
            raise ValueError("SwarmExecutionTracker requires either db or session_factory.")
        yield self.db

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _next_sequence_index(ctx: Mapping[str, Any]) -> int:
        value = ctx.get("next_sequence_index")
        if value is None:
            return 1
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _execution_context(state: SwarmState) -> Dict[str, Any]:
        raw = state.get("execution_context")
        if isinstance(raw, dict):
            return dict(raw)
        return {}

    @staticmethod
    def _incoming_handoff_id(*, agent_name: AgentName, state: SwarmState) -> str | None:
        pending_handoff = state.get("pending_handoff")
        if isinstance(pending_handoff, dict) and pending_handoff.get("target_agent") == agent_name:
            handoff_id = pending_handoff.get("handoff_id")
            if handoff_id is not None:
                return str(handoff_id)

        for item in reversed(list(state.get("handoff_history") or [])):
            if isinstance(item, dict) and item.get("target_agent") == agent_name:
                handoff_id = item.get("handoff_id")
                if handoff_id is not None:
                    return str(handoff_id)
        return None

    @staticmethod
    def _result_output_json(result: AgentExecutionResult) -> Dict[str, Any]:
        if result.status == "final":
            return dict(result.final_output or {})
        return dict(result.output or {})

    @staticmethod
    def _error_text(output: Mapping[str, Any]) -> str | None:
        if not output:
            return None
        if "error" in output and output["error"] is not None:
            return str(output["error"])
        return json.dumps(dict(output), default=str)
