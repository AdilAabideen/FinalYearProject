from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agentic.payload_builder import build_pending_agent_payload
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


ACUITY_AGENTS = {"esi1_agent", "esi2_agent", "esi345_agent"}


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def _handoff_to_doctor_from(state: SwarmState, sources: set[str]) -> bool:
    for item in state.get("handoff_history", []):
        if item.get("target_agent") == "doctor_agent" and item.get("from_agent") in sources:
            return True
    return False


def doctor_gate_ready(state: SwarmState) -> bool:
    has_acuity = _handoff_to_doctor_from(state, ACUITY_AGENTS)
    has_vitals = _handoff_to_doctor_from(state, {"vitals_agent"})
    return has_acuity and has_vitals


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
            if item.from_agent in ACUITY_AGENTS:
                acuity_handoff = item
            if item.from_agent == "vitals_agent":
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


def _agent_node(agent_name: AgentName):
    def node(state: SwarmState) -> Command:
        pending_agent_payload = build_pending_agent_payload(agent_name, state)
        result = execute_stub_agent(
            agent_name=agent_name,
            pending_agent_payload=pending_agent_payload,
            state=state,
        )

        updates: Dict[str, Any] = {
            "active_agent": agent_name,
            "pending_agent_payload": pending_agent_payload,
            "completed_agents": [agent_name],
            "execution_trace": [
                {
                    "event": "agent_executed",
                    "agent": agent_name,
                    "status": result.status,
                    "output": result.output,
                    "payload_metadata": pending_agent_payload.get("metadata", {}),
                }
            ],
        }

        if result.status == "final":
            updates["final_output"] = result.final_output or {}
            updates["execution_trace"].append(
                {
                    "event": "final_output_created",
                    "agent": agent_name,
                    "final_output": result.final_output,
                }
            )
            return Command(goto=END, update=updates)

        if result.status == "error":
            updates["execution_trace"].append(
                {
                    "event": "agent_error",
                    "agent": agent_name,
                    "output": result.output,
                }
            )
            return Command(goto=END, update=updates)

        if result.handoff is None:
            updates["execution_trace"].append(
                {
                    "event": "missing_handoff",
                    "agent": agent_name,
                }
            )
            return Command(goto=END, update=updates)

        handoff_dict = result.handoff.model_dump()
        updates["pending_handoff"] = handoff_dict
        updates["handoff_history"] = [handoff_dict]
        updates["execution_trace"].append(
            {
                "event": "handoff_created",
                "from_agent": result.handoff.from_agent,
                "target_agent": result.handoff.target_agent,
                "handoff_name": result.handoff.handoff_name,
            }
        )

        if result.handoff.target_agent == "doctor_agent":
            return Command(goto="doctor_gate", update=updates)
        return Command(goto=result.handoff.target_agent, update=updates)

    return node


def bootstrap(state: SwarmState) -> Dict[str, Any]:
    return {
        "execution_trace": [
            {
                "event": "bootstrap",
                "parallel_start_agents": list(parallel_start_agents),
            }
        ]
    }


def route_bootstrap(state: SwarmState) -> List[str]:
    return list(parallel_start_agents)


def doctor_gate(state: SwarmState) -> Dict[str, Any]:
    ready = doctor_gate_ready(state)
    return {
        "execution_trace": [
            {
                "event": "doctor_gate",
                "ready": ready,
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


def build_graph():
    graph = StateGraph(SwarmState)
    graph.add_node("bootstrap", bootstrap)
    graph.add_node("doctor_gate", doctor_gate)
    graph.add_node("esi1_agent", _agent_node("esi1_agent"))
    graph.add_node("esi2_agent", _agent_node("esi2_agent"))
    graph.add_node("esi345_agent", _agent_node("esi345_agent"))
    graph.add_node("vitals_agent", _agent_node("vitals_agent"))
    graph.add_node("doctor_agent", _agent_node("doctor_agent"))

    graph.add_edge(START, "bootstrap")
    graph.add_conditional_edges("bootstrap", route_bootstrap)
    graph.add_conditional_edges("doctor_gate", route_doctor_gate)
    return graph.compile()


def inspect_graph() -> None:
    print("=== Swarm V1 Graph Inspection ===")
    print("\nStart agents:")
    for agent in parallel_start_agents:
        print(f"- {agent}")

    print("\nFinalizing agents:")
    for agent in sorted(finalizing_agents):
        print(f"- {agent}")

    print("\nHandoff-tool agents:")
    for agent in sorted(handoff_tool_agents):
        print(f"- {agent}")

    print("\nAllowed handoffs:")
    for source, targets in allowed_handoffs.items():
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
        "doctor_gate",
        "doctor_agent",
    ]:
        print(f"- {node}")

    print("\nDoctor gate rule:")
    print("- requires at least one acuity handoff to doctor_agent")
    print("- requires one vitals_agent handoff to doctor_agent")

    print("\nMermaid:")
    print("flowchart LR")
    print('  START --> bootstrap')
    print('  bootstrap --> esi1_agent')
    print('  bootstrap --> vitals_agent')
    print('  esi1_agent --> esi2_agent')
    print('  esi1_agent --> doctor_gate')
    print('  esi2_agent --> esi345_agent')
    print('  esi2_agent --> doctor_gate')
    print('  esi345_agent --> doctor_gate')
    print('  vitals_agent --> doctor_gate')
    print('  doctor_gate --> doctor_agent')
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
    args = parser.parse_args()

    if args.inspect:
        inspect_graph()
        return
    if args.run:
        run_demo()
        return

    inspect_graph()
    print("\nTip: run with --run to execute the stubbed swarm demo.")


if __name__ == "__main__":
    main()
