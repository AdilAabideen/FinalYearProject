from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, HTTPException, status
from pydantic import ValidationError

from app.agentic.model_registry import get_chat_model, resolve_model_spec
from app.agentic.runtime import AgentRuntime, RuntimeConfig
from app.agentic.swarm import (
    AgentNodeExecutor,
    CallableExecutionStrategy,
    ExecutionRequest,
    GateEvaluator,
    SwarmEventEmitter,
    SwarmExecutionTracker,
    SwarmGraphBuilder,
)
from app.agentic.swarm_agent_registry import SwarmAgentRegistry
from app.agentic.swarm_contract import AgentExecutionResult, SwarmState, make_initial_swarm_state
from app.agentic.swarm_result_normalizer import normalize_agent_result
from app.agentic.telemetry.agent_trace_persistence import wire_agent_trace_persistence
from app.agentic.workflows.registry import get_workflow_definition, get_workflow_spec
from app.config import settings
from app.database import SessionLocal
from app.schemas.swarm_execution import SwarmExecutionStartRequest, SwarmExecutionStartResponse
from app.schemas.swarm_runs import SwarmRunCreateRequest
from app.api.services import swarm_runs_service


def _build_real_registry() -> SwarmAgentRegistry:
    model_id = settings.OPENAI_MODEL
    model_spec = resolve_model_spec(model_id)
    runtime = AgentRuntime(
        model_id=model_id,
        model_spec=model_spec,
        model=get_chat_model(model_id),
    )
    return SwarmAgentRegistry(
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
    registry: SwarmAgentRegistry,
    execution_tracker: SwarmExecutionTracker,
):
    workflow = get_workflow_definition(workflow_id)

    async def _execute(request: ExecutionRequest) -> AgentExecutionResult:
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
    return SwarmGraphBuilder(
        workflow=workflow,
        agent_executor=executor,
        gate_evaluator=gate_evaluator,
    ).build()


def normalize_workflow_input(
    workflow_id: str,
    input_payload: dict[str, Any],
) -> tuple[dict[str, Any], str, str | None]:
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


def create_and_start_swarm_run(
    *,
    workflow_id: str,
    input_payload: dict[str, Any],
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[str, dict[str, Any], str, str | None]:
    normalized_input, input_schema_name, workflow_version = normalize_workflow_input(
        workflow_id,
        input_payload,
    )

    db = SessionLocal()
    try:
        create_response = swarm_runs_service.create_swarm_run(
            SwarmRunCreateRequest(
                workflow_id=workflow_id,
                workflow_version=workflow_version,
                input_schema_name=input_schema_name,
                input=normalized_input,
                metadata=metadata,
            ),
            db,
        )
        swarm_runs_service.start_swarm_run(create_response.swarm_run_id, db)
    finally:
        db.close()

    return (
        create_response.swarm_run_id,
        normalized_input,
        input_schema_name,
        workflow_version,
    )


def _run_urls(swarm_run_id: str) -> dict[str, str]:
    base = f"/api/swarm-runs/{swarm_run_id}"
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


def start_swarm_execution(
    workflow_id: str,
    payload: SwarmExecutionStartRequest,
    background_tasks: BackgroundTasks,
) -> SwarmExecutionStartResponse:
    swarm_run_id, normalized_input, input_schema_name, workflow_version = create_and_start_swarm_run(
        workflow_id=workflow_id,
        input_payload=payload.input,
        metadata={
            "source": "mas_execution_api",
            **dict(payload.metadata or {}),
        },
    )

    background_tasks.add_task(
        _execute_swarm_run_in_background,
        workflow_id,
        workflow_version,
        swarm_run_id,
        normalized_input,
    )

    urls = _run_urls(swarm_run_id)
    return SwarmExecutionStartResponse(
        swarm_run_id=swarm_run_id,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        input_schema_name=input_schema_name,
        status="running",
        **urls,
    )


def _execute_swarm_run_in_background(
    workflow_id: str,
    workflow_version: str | None,
    swarm_run_id: str,
    case_info: dict[str, Any],
) -> None:
    asyncio.run(
        execute_swarm_run(
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            swarm_run_id=swarm_run_id,
            case_info=case_info,
        )
    )


async def execute_swarm_run(
    *,
    workflow_id: str,
    workflow_version: str | None,
    swarm_run_id: str,
    case_info: dict[str, Any],
) -> SwarmState:
    workflow = get_workflow_definition(workflow_id)
    registry = _build_real_registry()
    event_emitter = SwarmEventEmitter(
        workflow_id=workflow_id,
        session_factory=SessionLocal,
    )
    tracker = SwarmExecutionTracker(
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
    initial_state = make_initial_swarm_state(
        case_info,
        execution_context={
            "swarm_run_id": swarm_run_id,
            "workflow_id": workflow_id,
            "workflow_version": workflow_version,
            "next_sequence_index": 1,
        },
    )
    event_emitter.emit(
        swarm_run_id=swarm_run_id,
        event_type="swarm_started",
        status="running",
        payload_json={
            "workflow_id": workflow_id,
            "workflow_version": workflow_version,
            "input": case_info,
        },
    )

    db = SessionLocal()
    try:
        result = await graph.ainvoke(initial_state)
        execution_context = dict(result.get("execution_context") or {})
        event_emitter.emit(
            swarm_run_id=swarm_run_id,
            event_type="swarm_completed",
            status="completed",
            agent_run_id=execution_context.get("current_agent_run_id"),
            payload_json={
                "workflow_id": workflow_id,
                "workflow_version": workflow.metadata.version,
                "final_output": result.get("final_output"),
            },
        )
        swarm_runs_service.finalize_swarm_run(
            swarm_run_id,
            db,
            status="completed",
            final_output_json=result.get("final_output"),
            current_agent_run_id=execution_context.get("current_agent_run_id"),
            current_gate_id=execution_context.get("current_gate_id"),
        )
        return result
    except Exception as exc:
        event_emitter.emit(
            swarm_run_id=swarm_run_id,
            event_type="swarm_failed",
            status="failed",
            payload_json={
                "workflow_id": workflow_id,
                "workflow_version": workflow.metadata.version,
                "error": str(exc),
            },
        )
        swarm_runs_service.finalize_swarm_run(
            swarm_run_id,
            db,
            status="failed",
            error_text=str(exc),
        )
        raise
    finally:
        db.close()
