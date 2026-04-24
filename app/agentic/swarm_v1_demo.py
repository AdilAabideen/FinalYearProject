#swarm_v1_demo
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send

from app.agentic.model_registry import get_chat_model, resolve_model_spec
from app.agentic.runtime import AgentRuntime, RuntimeConfig
from app.agentic.swarm_agent_registry import SwarmAgentRegistry
from app.agentic.swarm_contract import (
    AgentExecutionResult,
    AgentName,
    HandoffEnvelope,
    SwarmState,
    agent_can_finalize,
    allowed_handoffs,
    finalizing_agents,
    handoff_tool_agents,
    make_initial_swarm_state,
    parallel_start_agents,
)
from app.agentic.swarm_result_normalizer import normalize_agent_result
from app.agentic.swarm import (
    AgentNodeExecutionOutcome,
    AgentNodeExecutor,
    CallableExecutionStrategy,
    ExecutionRequest,
    SyncCallableExecutionStrategy,
)
from app.agentic.workflows.registry import get_workflow_definition
from app.config import settings

WORKFLOW = get_workflow_definition("esi_swarm_v1")
DOCTOR_GATE_ID = WORKFLOW.workflow_metadata.get("doctor_gate_id", "doctor_gate")


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def doctor_gate_ready(state: SwarmState) -> bool:
    return WORKFLOW.is_gate_ready(
        DOCTOR_GATE_ID,
        list(state.get("handoff_history", [])),
    )


def _validated_handoff_history(state: SwarmState) -> List[HandoffEnvelope]:
    history: List[HandoffEnvelope] = []
    for item in state.get("handoff_history", []):
        if not isinstance(item, dict):
            continue
        try:
            history.append(HandoffEnvelope.model_validate(item))
        except Exception:
            continue
    return history


def _llm_payload_case_info(payload: Dict[str, Any]) -> Dict[str, Any]:
    llm_payload = payload.get("llm_payload")
    if not isinstance(llm_payload, dict):
        return {}
    case_info = llm_payload.get("case_info")
    return dict(case_info) if isinstance(case_info, dict) else {}


def _handoff(
    *,
    handoff_name: str,
    from_agent: AgentName,
    target_agent: AgentName,
    payload_schema: str,
    payload: Dict[str, Any],
) -> HandoffEnvelope:
    return HandoffEnvelope(
        handoff_name=handoff_name,
        from_agent=from_agent,
        target_agent=target_agent,
        payload_schema=payload_schema,
        payload=payload,
    )


def execute_stub_agent(
    *,
    agent_name: AgentName,
    pending_agent_payload: Dict[str, Any],
    state: SwarmState,
) -> AgentExecutionResult:
    case_info = _llm_payload_case_info(pending_agent_payload)

    if agent_name == "esi1_agent":
        if bool(case_info.get("needs_immediate_lifesaving_intervention")):
            handoff = _handoff(
                handoff_name="handoff_to_doctor_agent",
                from_agent="esi1_agent",
                target_agent="doctor_agent",
                payload_schema="ESI1ToDoctorPayload",
                payload={
                    "decision": "esi1",
                    "urgency": "critical",
                    "reason": "Immediate life-saving intervention criteria are present.",
                    "critical_concerns": ["immediate_lifesaving_intervention"],
                    "request": "Doctor review required for ESI-1 confirmation.",
                },
            )
            return AgentExecutionResult(
                agent_name=agent_name,
                status="handoff",
                output={"stub_decision": "esi1"},
                handoff=handoff,
            )

        handoff = _handoff(
            handoff_name="handoff_to_esi2_agent",
            from_agent="esi1_agent",
            target_agent="esi2_agent",
            payload_schema="ESI1ToESI2Payload",
            payload={
                "esi1_result": "not_esi1",
                "brief_reason": "No immediate life-saving intervention requirement found.",
                "carry_forward_concerns": ["continue_high_risk_screen"],
                "focus_for_esi2": "Assess high-risk presentation and likely deterioration.",
            },
        )
        return AgentExecutionResult(
            agent_name=agent_name,
            status="handoff",
            output={"stub_decision": "not_esi1"},
            handoff=handoff,
        )

    if agent_name == "esi2_agent":
        if bool(case_info.get("high_risk_situation")):
            handoff = _handoff(
                handoff_name="handoff_to_doctor_agent",
                from_agent="esi2_agent",
                target_agent="doctor_agent",
                payload_schema="ESI2ToDoctorPayload",
                payload={
                    "decision": "esi2",
                    "urgency": "high",
                    "reason": "High-risk presentation detected.",
                    "critical_concerns": ["high_risk_situation"],
                    "request": "Doctor review required for ESI-2 confirmation.",
                },
            )
            return AgentExecutionResult(
                agent_name=agent_name,
                status="handoff",
                output={"stub_decision": "esi2"},
                handoff=handoff,
            )

        handoff = _handoff(
            handoff_name="handoff_to_esi345_agent",
            from_agent="esi2_agent",
            target_agent="esi345_agent",
            payload_schema="ESI2ToESI345Payload",
            payload={
                "esi2_result": "not_esi2",
                "brief_reason": "No high-risk or deterioration criteria detected.",
                "carry_forward_concerns": ["predict_resources"],
                "focus_for_esi345": "Predict ESI-counted resources.",
            },
        )
        return AgentExecutionResult(
            agent_name=agent_name,
            status="handoff",
            output={"stub_decision": "not_esi2"},
            handoff=handoff,
        )

    if agent_name == "esi345_agent":
        esi_level = int(case_info.get("predicted_esi", 3))
        handoff = _handoff(
            handoff_name="handoff_to_doctor_agent",
            from_agent="esi345_agent",
            target_agent="doctor_agent",
            payload_schema="ESI345ToDoctorPayload",
            payload={
                "decision": "resource_prediction_complete",
                "urgency": "routine",
                "reason": "Acuity branch completed ESI-3/4/5 prediction.",
                "esi_level": esi_level,
                "num_resources": int(case_info.get("predicted_resources_count", 2)),
                "predicted_resources": list(case_info.get("predicted_resources", ["labs", "radiograph"])),
                "critical_concerns": [],
                "request": "Doctor should merge acuity and vitals handoffs.",
            },
        )
        return AgentExecutionResult(
            agent_name=agent_name,
            status="handoff",
            output={"stub_decision": f"esi{esi_level}"},
            handoff=handoff,
        )

    if agent_name == "vitals_agent":
        handoff = _handoff(
            handoff_name="handoff_to_doctor_agent",
            from_agent="vitals_agent",
            target_agent="doctor_agent",
            payload_schema="VitalsToDoctorPayload",
            payload={
                "consider_uptriage": bool(case_info.get("danger_zone_flag")),
                "urgency": "high" if bool(case_info.get("danger_zone_flag")) else "low",
                "reason": "Vitals branch completed danger-zone review.",
                "abnormal_vitals": list(case_info.get("abnormal_vitals", [])),
                "confidence": "medium",
                "request": "Doctor should consider vitals during final review.",
            },
        )
        return AgentExecutionResult(
            agent_name=agent_name,
            status="handoff",
            output={"stub_decision": "vitals_review_complete"},
            handoff=handoff,
        )

    if agent_name == "doctor_agent":
        acuity_handoff = None
        vitals_handoff = None
        handoff_history = _validated_handoff_history(state)
        for item in handoff_history:
            if item.target_agent != "doctor_agent":
                continue
            if "acuity" in WORKFLOW.sources_for_agent(item.from_agent):
                acuity_handoff = item
            if "vitals" in WORKFLOW.sources_for_agent(item.from_agent):
                vitals_handoff = item

        if acuity_handoff is None or vitals_handoff is None:
            return AgentExecutionResult(
                agent_name=agent_name,
                status="error",
                output={"error": "doctor_missing_required_handoffs"},
            )

        final_esi = acuity_handoff.payload.get("esi_level")
        if final_esi is None:
            final_esi = 1 if acuity_handoff.from_agent == "esi1_agent" else 2
        if bool(vitals_handoff.payload.get("consider_uptriage")):
            final_esi = min(int(final_esi), 2)

        return AgentExecutionResult(
            agent_name=agent_name,
            status="final",
            output={"stub_decision": "finalized"},
            final_output={
                "ok": True,
                "final_esi": int(final_esi),
                "acuity_from": acuity_handoff.from_agent,
                "vitals_consider_uptriage": bool(vitals_handoff.payload.get("consider_uptriage")),
                "handoff_count": len(handoff_history),
            },
        )

    return AgentExecutionResult(
        agent_name=agent_name,
        status="error",
        output={"error": "unknown_agent"},
    )


def _outcome_to_command(outcome: AgentNodeExecutionOutcome) -> Command:
    if outcome.terminal or outcome.goto is None:
        return Command(goto=END, update=outcome.state_updates)
    return Command(goto=outcome.goto, update=outcome.state_updates)


def _build_stub_executor() -> AgentNodeExecutor:
    def _execute(request: ExecutionRequest) -> AgentExecutionResult:
        return execute_stub_agent(
            agent_name=request.agent_name,
            pending_agent_payload=request.payload_dict(),
            state=request.state_dict(),  # type: ignore[arg-type]
        )

    return AgentNodeExecutor(
        workflow=WORKFLOW,
        strategy=SyncCallableExecutionStrategy(
            mode="stub",
            execute_fn=_execute,
        ),
    )


def _build_real_executor(registry: SwarmAgentRegistry) -> AgentNodeExecutor:
    async def _execute(request: ExecutionRequest) -> AgentExecutionResult:
        agent = registry.get(request.agent_name)
        state = request.state_dict()
        run_id = str((state.get("case_info") or {}).get("case_id") or request.workflow_id)
        agent.set_event_context(run_id=run_id, agent_name=request.agent_name)
        raw_result = await agent.ainvoke(request.payload_dict())
        return normalize_agent_result(request.agent_name, raw_result)

    return AgentNodeExecutor(
        workflow=WORKFLOW,
        strategy=CallableExecutionStrategy(
            mode="real",
            execute_fn=_execute,
        ),
    )


def _stub_agent_node(agent_name: AgentName, executor: AgentNodeExecutor):
    def node(state: SwarmState) -> Command:
        outcome = executor.execute_sync(agent_name=agent_name, state=state)
        return _outcome_to_command(outcome)

    return node


def _real_agent_node(agent_name: AgentName, executor: AgentNodeExecutor):
    async def node(state: SwarmState) -> Command:
        outcome = await executor.execute(agent_name=agent_name, state=state)
        return _outcome_to_command(outcome)

    return node


def bootstrap(state: SwarmState) -> Dict[str, Any]:
    return {
        "execution_trace": [
            {
                "event": "bootstrap",
                "parallel_start_agents": list(WORKFLOW.start_agents),
            }
        ]
    }


def _bootstrap_branch_state(state: SwarmState) -> SwarmState:
    return make_initial_swarm_state(dict(state.get("case_info") or {}))


def route_bootstrap(state: SwarmState) -> List[Send]:
    branch_state = _bootstrap_branch_state(state)
    return [Send(agent_name, dict(branch_state)) for agent_name in WORKFLOW.start_agents]


def doctor_gate(state: SwarmState) -> Dict[str, Any]:
    ready = doctor_gate_ready(state)
    satisfied_sources = list(
        WORKFLOW.gate_satisfied_sources(
            DOCTOR_GATE_ID,
            list(state.get("handoff_history", [])),
        )
    )
    missing_sources = list(
        WORKFLOW.gate_missing_sources(
            DOCTOR_GATE_ID,
            list(state.get("handoff_history", [])),
        )
    )
    return {
        "execution_trace": [
            {
                "event": "doctor_gate",
                "ready": ready,
                "satisfied_sources": satisfied_sources,
                "missing_sources": missing_sources,
                "handoffs_to_doctor": [
                    item
                    for item in state.get("handoff_history", [])
                    if item.get("target_agent") == "doctor_agent"
                ],
            }
        ]
    }


def route_doctor_gate(state: SwarmState) -> str:
    if state.get("final_output") is not None:
        return END
    if doctor_gate_ready(state):
        return "doctor_agent"
    return END


def build_graph(*, registry: Optional[SwarmAgentRegistry] = None):
    graph = StateGraph(SwarmState)
    graph.add_node("bootstrap", bootstrap)
    graph.add_node(DOCTOR_GATE_ID, doctor_gate)
    if registry is None:
        executor = _build_stub_executor()
        graph.add_node("esi1_agent", _stub_agent_node("esi1_agent", executor))
        graph.add_node("esi2_agent", _stub_agent_node("esi2_agent", executor))
        graph.add_node("esi345_agent", _stub_agent_node("esi345_agent", executor))
        graph.add_node("vitals_agent", _stub_agent_node("vitals_agent", executor))
        graph.add_node("doctor_agent", _stub_agent_node("doctor_agent", executor))
    else:
        executor = _build_real_executor(registry)
        graph.add_node("esi1_agent", _real_agent_node("esi1_agent", executor))
        graph.add_node("esi2_agent", _real_agent_node("esi2_agent", executor))
        graph.add_node("esi345_agent", _real_agent_node("esi345_agent", executor))
        graph.add_node("vitals_agent", _real_agent_node("vitals_agent", executor))
        graph.add_node("doctor_agent", _real_agent_node("doctor_agent", executor))

    graph.add_edge(START, "bootstrap")
    graph.add_conditional_edges("bootstrap", route_bootstrap)
    graph.add_conditional_edges(DOCTOR_GATE_ID, route_doctor_gate)
    return graph.compile()


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


def run_demo() -> None:
    graph = build_graph()
    result = graph.invoke(make_initial_swarm_state(demo_case()))
    print_run_result(result)


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
    registry = build_real_registry()
    graph = build_graph(registry=registry)
    result = await graph.ainvoke(make_initial_swarm_state(demo_case()))
    print_run_result(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Terminal-only Swarm V1 graph demo.")
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print graph wiring and contract details without executing the swarm.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the stubbed multi-agent swarm demo.",
    )
    parser.add_argument(
        "--run-stub",
        action="store_true",
        help="Run the stubbed multi-agent swarm demo.",
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
    if args.run or args.run_stub:
        run_demo()
        return
    if args.run_real:
        asyncio.run(run_real_demo())
        return

    inspect_graph()
    print("\nTip: run with --run to execute the stubbed swarm demo or --run-real for real agents.")


if __name__ == "__main__":
    main()
