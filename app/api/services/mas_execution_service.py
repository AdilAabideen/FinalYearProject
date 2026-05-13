"""Mas Execution Service service helpers."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, HTTPException, status
from pydantic import ValidationError

from app.agentic.model_registry import get_chat_model, resolve_model_spec, validate_model_for_agent
from app.agentic.runtime import AgentRuntime, RuntimeConfig
from app.agentic.mas import (
    AgentNodeExecutor,
    CallableExecutionStrategy,
    ExecutionRequest,
    GateEvaluator,
    MASEventEmitter,
    MASExecutionTracker,
    MASGraphBuilder,
)
from app.agentic.mas_agent_registry import MASAgentRegistry
from app.agentic.mas_contract import AgentExecutionResult, MASState, make_initial_mas_state
from app.agentic.mas_result_normalizer import normalize_agent_result
from app.agentic.telemetry.agent_trace_persistence import wire_agent_trace_persistence
from app.agentic.workflows.registry import get_workflow_definition, get_workflow_spec
from app.config import settings
from app.database import SessionLocal
from app.schemas.mas_execution import MASExecutionStartRequest, MASExecutionStartResponse
from app.schemas.mas_runs import MASRunCreateRequest
from app.api.services import mas_runs_service


def _build_real_registry(model_id: str) -> MASAgentRegistry:
    """Build real registry."""
    # Build the next value.
    model_spec = resolve_model_spec(model_id)
    runtime = AgentRuntime(
        model_id=model_id,
        model_spec=model_spec,
        model=get_chat_model(model_id),
    )
    return MASAgentRegistry(
        runtime=runtime,
        runtime_config=RuntimeConfig(
            multi_agent=True,
            print_events=False,
            persist_events=True,
        ),
    )


def _build_graph(
    *,
    workflow_id: str,
    registry: MASAgentRegistry,
    execution_tracker: MASExecutionTracker,
):
    """Build graph."""
    # Build the next value.
    workflow = get_workflow_definition(workflow_id)

    async def _execute(request: ExecutionRequest) -> AgentExecutionResult:
        """Handle the value."""
        # Keep the main step clear.
        agent = registry.get(request.agent_name)
        state = request.state_dict()
        execution_context = dict(state.get("execution_context") or {})
        run_id = str(
            execution_context.get("current_agent_run_id")
            or request.workflow_id
        )
        wire_agent_trace_persistence(
            agent=agent,
            session_factory=SessionLocal,
            run_id=run_id,
            agent_name=request.agent_name,
            agent_system="handrolled_callback",
            model_name=registry.runtime.model_id,
            model_spec=registry.runtime.model_spec,
            start_seq=0,
        )
        raw_result = await agent.ainvoke(request.payload_dict())
        return normalize_agent_result(request.agent_name, raw_result)

    executor = AgentNodeExecutor(
        workflow=workflow,
        strategy=CallableExecutionStrategy(
            mode="real",
            execute_fn=_execute,
        ),
        execution_tracker=execution_tracker,
    )
    gate_evaluator = GateEvaluator(
        workflow=workflow,
        execution_tracker=execution_tracker,
    )
    return MASGraphBuilder(
        workflow=workflow,
        agent_executor=executor,
        gate_evaluator=gate_evaluator,
    ).build()


def normalize_workflow_input(
    workflow_id: str,
    input_payload: dict[str, Any],
) -> tuple[dict[str, Any], str, str | None]:
    """Normalize workflow input."""
    # Keep the output consistent.
    try:
        workflow_spec = get_workflow_spec(workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        validated = workflow_spec.input_schema.model.model_validate(input_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    normalized_input = validated.model_dump(mode="json")
    return (
        normalized_input,
        workflow_spec.input_schema.schema_name,
        workflow_spec.version,
    )


def create_and_start_mas_run(
    *,
    workflow_id: str,
    input_payload: dict[str, Any],
    model_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[str, dict[str, Any], str, str | None]:
    """Create and start MAS run."""
    # Build the new value.
    normalized_input, input_schema_name, workflow_version = normalize_workflow_input(
        workflow_id,
        input_payload,
    )

    db = SessionLocal()
    try:
        create_response = mas_runs_service.create_mas_run(
            MASRunCreateRequest(
                workflow_id=workflow_id,
                workflow_version=workflow_version,
                input_schema_name=input_schema_name,
                input=normalized_input,
                metadata={
                    "model_id": model_id,
                    **dict(metadata or {}),
                },
            ),
            db,
        )
        mas_runs_service.start_mas_run(create_response.mas_run_id, db)
    finally:
        db.close()

    return (
        create_response.mas_run_id,
        normalized_input,
        input_schema_name,
        workflow_version,
    )


def _run_urls(mas_run_id: str) -> dict[str, str]:
    """Run urls."""
    # Kick off the main step.
    base = f"/api/swarm-runs/{mas_run_id}"
    return {
        "run_url": base,
        "summary_url": f"{base}/summary",
        "events_url": f"{base}/events",
        "events_stream_url": f"{base}/events/stream",
        "agents_url": f"{base}/agents",
        "handoffs_url": f"{base}/handoffs",
        "gate_evaluations_url": f"{base}/gate-evaluations",
        "final_output_url": f"{base}/final-output",
    }


def start_mas_execution(
    workflow_id: str,
    payload: MASExecutionStartRequest,
    background_tasks: BackgroundTasks,
) -> MASExecutionStartResponse:
    """Start mas execution."""
    # Kick off the main step.
    workflow = get_workflow_definition(workflow_id)
    model_id = payload.model_id or settings.OPENAI_MODEL
    for agent_name in workflow.participating_agents:
        validate_model_for_agent(
            model_id=model_id,
            agent_name=agent_name,
            requires_tools=True,
        )

    mas_run_id, normalized_input, input_schema_name, workflow_version = create_and_start_mas_run(
        workflow_id=workflow_id,
        input_payload=payload.input,
        model_id=model_id,
        metadata={
            "source": "mas_execution_api",
            **dict(payload.metadata or {}),
        },
    )

    background_tasks.add_task(
        _execute_mas_run_in_background,
        workflow_id,
        workflow_version,
        mas_run_id,
        normalized_input,
        model_id,
    )

    urls = _run_urls(mas_run_id)
    return MASExecutionStartResponse(
        mas_run_id=mas_run_id,
        swarm_run_id=mas_run_id,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        input_schema_name=input_schema_name,
        model_id=model_id,
        status="running",
        **urls,
    )


def _execute_mas_run_in_background(
    workflow_id: str,
    workflow_version: str | None,
    mas_run_id: str,
    case_info: dict[str, Any],
    model_id: str,
) -> None:
    """Handle mas run in background."""
    # Keep the main step clear.
    asyncio.run(
        execute_mas_run(
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            mas_run_id=mas_run_id,
            case_info=case_info,
            model_id=model_id,
        )
    )


async def execute_mas_run(
    *,
    workflow_id: str,
    workflow_version: str | None,
    mas_run_id: str,
    case_info: dict[str, Any],
    model_id: str,
) -> MASState:
    """Handle mas run."""
    # Keep the main step clear.
    workflow = get_workflow_definition(workflow_id)
    registry = _build_real_registry(model_id)
    event_emitter = MASEventEmitter(
        workflow_id=workflow_id,
        session_factory=SessionLocal,
    )
    tracker = MASExecutionTracker(
        session_factory=SessionLocal,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        event_emitter=event_emitter,
    )
    graph = _build_graph(
        workflow_id=workflow_id,
        registry=registry,
        execution_tracker=tracker,
    )
    initial_state = make_initial_mas_state(
        case_info,
        execution_context={
            "mas_run_id": mas_run_id,
            "workflow_id": workflow_id,
            "workflow_version": workflow_version,
            "model_id": model_id,
            "next_sequence_index": 1,
        },
    )
    event_emitter.emit(
        mas_run_id=mas_run_id,
        event_type="mas_started",
        status="running",
        payload_json={
            "workflow_id": workflow_id,
            "workflow_version": workflow_version,
            "model_id": model_id,
            "input": case_info,
        },
    )

    db = SessionLocal()
    try:
        result = await graph.ainvoke(initial_state)
        execution_context = dict(result.get("execution_context") or {})
        event_emitter.emit(
            mas_run_id=mas_run_id,
            event_type="mas_completed",
            status="completed",
            agent_run_id=execution_context.get("current_agent_run_id"),
            payload_json={
                "workflow_id": workflow_id,
                "workflow_version": workflow.metadata.version,
                "model_id": model_id,
                "final_output": result.get("final_output"),
            },
        )
        mas_runs_service.finalize_mas_run(
            mas_run_id,
            db,
            status="completed",
            final_output_json=result.get("final_output"),
            current_agent_run_id=execution_context.get("current_agent_run_id"),
            current_gate_id=execution_context.get("current_gate_id"),
        )
        return result
    except Exception as exc:
        event_emitter.emit(
            mas_run_id=mas_run_id,
            event_type="mas_failed",
            status="failed",
            payload_json={
                "workflow_id": workflow_id,
                "workflow_version": workflow.metadata.version,
                "model_id": model_id,
                "error": str(exc),
            },
        )
        mas_runs_service.finalize_mas_run(
            mas_run_id,
            db,
            status="failed",
            error_text=str(exc),
        )
        raise
    finally:
        db.close()
