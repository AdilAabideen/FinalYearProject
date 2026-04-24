#swarm_v1_demo
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.agentic.model_registry import get_chat_model, resolve_model_spec
from app.agentic.runtime import AgentRuntime, RuntimeConfig
from app.agentic.swarm_agent_registry import SwarmAgentRegistry
from app.agentic.swarm_contract import (
    AgentExecutionResult,
    AgentName,
    SwarmState,
    finalizing_agents,
    handoff_tool_agents,
    make_initial_swarm_state,
)
from app.agentic.swarm_result_normalizer import normalize_agent_result
from app.agentic.swarm import (
    AgentNodeExecutor,
    CallableExecutionStrategy,
    ExecutionRequest,
    GateEvaluator,
    SwarmExecutionTracker,
    SwarmGraphBuilder,
)
from app.api.services import swarm_runs_service
from app.database import SessionLocal
from app.schemas.swarm_runs import SwarmRunCreateRequest
from app.agentic.workflows.registry import get_workflow_definition
from app.config import settings

WORKFLOW = get_workflow_definition("esi_swarm_v1")
DOCTOR_GATE_ID = WORKFLOW.workflow_metadata.get("doctor_gate_id", "doctor_gate")


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)

def _build_real_executor(
    registry: SwarmAgentRegistry,
    *,
    execution_tracker: SwarmExecutionTracker | None = None,
) -> AgentNodeExecutor:
    async def _execute(request: ExecutionRequest) -> AgentExecutionResult:
        agent = registry.get(request.agent_name)
        state = request.state_dict()
        execution_context = dict(state.get("execution_context") or {})
        run_id = str(
            execution_context.get("current_agent_run_id")
            or (state.get("case_info") or {}).get("case_id")
            or request.workflow_id
        )
        agent.set_event_context(run_id=run_id, agent_name=request.agent_name)
        raw_result = await agent.ainvoke(request.payload_dict())
        return normalize_agent_result(request.agent_name, raw_result)

    return AgentNodeExecutor(
        workflow=WORKFLOW,
        strategy=CallableExecutionStrategy(
            mode="real",
            execute_fn=_execute,
        ),
        execution_tracker=execution_tracker,
    )


def build_graph(
    *,
    registry: SwarmAgentRegistry,
    execution_tracker: SwarmExecutionTracker | None = None,
):
    executor = _build_real_executor(registry, execution_tracker=execution_tracker)
    gate_evaluator = GateEvaluator(workflow=WORKFLOW)
    return SwarmGraphBuilder(
        workflow=WORKFLOW,
        agent_executor=executor,
        gate_evaluator=gate_evaluator,
    ).build()


def inspect_graph() -> None:
    print("=== Swarm V1 Graph Inspection ===")
    print("\nStart agents:")
    for agent in WORKFLOW.start_agents:
        print(f"- {agent}")

    print("\nFinalizing agents:")
    for agent in sorted(finalizing_agents):
        print(f"- {agent}")

    print("\nHandoff-tool agents:")
    for agent in sorted(handoff_tool_agents):
        print(f"- {agent}")

    print("\nAllowed handoffs:")
    for source, targets in WORKFLOW.allowed_handoffs.items():
        if not targets:
            print(f"- {source} -> none")
            continue
        for target in sorted(targets):
            print(f"- {source} -> {target}")

    print("\nGraph nodes:")
    for node in [
        "bootstrap",
        "esi1_agent",
        "vitals_agent",
        "esi2_agent",
        "esi345_agent",
        DOCTOR_GATE_ID,
        "doctor_agent",
    ]:
        print(f"- {node}")

    print("\nDoctor gate rule:")
    gate = WORKFLOW.gates[DOCTOR_GATE_ID]
    print("- required sources: {sources}".format(sources=", ".join(gate.required_sources)))
    print("- source mapping:")
    for source_id in gate.required_sources:
        print("  {source}: {agents}".format(source=source_id, agents=", ".join(WORKFLOW.source_agents(source_id))))

    print("\nMermaid:")
    print("flowchart LR")
    print('  START --> bootstrap')
    print('  bootstrap --> esi1_agent')
    print('  bootstrap --> vitals_agent')
    print('  esi1_agent --> esi2_agent')
    print(f'  esi1_agent --> {DOCTOR_GATE_ID}')
    print('  esi2_agent --> esi345_agent')
    print(f'  esi2_agent --> {DOCTOR_GATE_ID}')
    print(f'  esi345_agent --> {DOCTOR_GATE_ID}')
    print(f'  vitals_agent --> {DOCTOR_GATE_ID}')
    print(f'  {DOCTOR_GATE_ID} --> doctor_agent')
    print('  doctor_agent --> END')


def demo_case() -> Dict[str, Any]:
    return {
        "case_id": "demo-001",
        "chiefcomplaint": "abdominal pain with abnormal vitals",
        "needs_immediate_lifesaving_intervention": False,
        "high_risk_situation": False,
        "predicted_esi": 3,
        "predicted_resources_count": 2,
        "predicted_resources": ["labs", "CT"],
        "danger_zone_flag": True,
        "abnormal_vitals": ["tachycardia", "hypotension"],
    }


def print_run_result(result: SwarmState) -> None:
    print("=== Swarm V1 Run Result ===")
    print("\nExecution trace:")
    for event in result.get("execution_trace", []):
        print(f"- {event}")

    print("\nHandoff history:")
    for handoff in result.get("handoff_history", []):
        print(f"- {handoff.get('from_agent')} -> {handoff.get('target_agent')} ({handoff.get('handoff_name')})")
        print(f"  payload: {_json(handoff.get('payload', {}))}")

    print("\nCompleted agents:")
    for agent in result.get("completed_agents", []):
        print(f"- {agent}")

    print("\nLast pending agent payload:")
    print(_json(result.get("pending_agent_payload")))

    print("\nFinal output:")
    print(_json(result.get("final_output")))


def build_real_registry() -> SwarmAgentRegistry:
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
            print_events=True,
            persist_events=False,
        ),
    )


async def run_real_demo() -> None:
    db: Session = SessionLocal()
    registry = build_real_registry()
    case = demo_case()
    create_response = swarm_runs_service.create_swarm_run(
        SwarmRunCreateRequest(
            workflow_id=WORKFLOW.metadata.workflow_id,
            workflow_version=WORKFLOW.metadata.version,
            case_id=str(case.get("case_id")) if case.get("case_id") is not None else None,
            input_schema_name=None,
            input=case,
            metadata={
                "source": "swarm_v1_demo",
                "workflow_name": WORKFLOW.metadata.name,
            },
        ),
        db,
    )
    swarm_runs_service.start_swarm_run(create_response.swarm_run_id, db)

    tracker = SwarmExecutionTracker(
        db=db,
        workflow_id=WORKFLOW.metadata.workflow_id,
        workflow_version=WORKFLOW.metadata.version,
    )
    graph = build_graph(registry=registry, execution_tracker=tracker)
    initial_state = make_initial_swarm_state(
        case,
        execution_context={
            "swarm_run_id": create_response.swarm_run_id,
            "workflow_id": WORKFLOW.metadata.workflow_id,
            "workflow_version": WORKFLOW.metadata.version,
            "next_sequence_index": 1,
        },
    )

    try:
        result = await graph.ainvoke(initial_state)
        execution_context = dict(result.get("execution_context") or {})
        swarm_runs_service.finalize_swarm_run(
            create_response.swarm_run_id,
            db,
            status="completed",
            final_output_json=result.get("final_output"),
            current_agent_run_id=execution_context.get("current_agent_run_id"),
        )
        print_run_result(result)
    except Exception as exc:
        swarm_runs_service.finalize_swarm_run(
            create_response.swarm_run_id,
            db,
            status="failed",
            error_text=str(exc),
        )
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Terminal-only Swarm V1 graph demo.")
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print graph wiring and contract details without executing the swarm.",
    )
    parser.add_argument(
        "--run-real",
        action="store_true",
        help="Run the real multi-agent swarm demo with terminal telemetry and no persistence.",
    )
    args = parser.parse_args()

    if args.inspect:
        inspect_graph()
        return
    if args.run_real:
        asyncio.run(run_real_demo())
        return

    inspect_graph()
    print("\nTip: run with --run-real to execute the real multi-agent swarm demo.")


if __name__ == "__main__":
    main()
