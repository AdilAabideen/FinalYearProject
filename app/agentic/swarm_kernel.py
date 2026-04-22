from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Annotated, Any, Callable, Dict, List, Optional, Tuple, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field


def _merge_dicts(
    left: Optional[Dict[str, Any]],
    right: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(left or {})
    merged.update(right or {})
    return merged


def _merge_unique_str_lists(
    left: Optional[List[str]],
    right: Optional[List[str]],
) -> List[str]:
    values: List[str] = []
    for item in list(left or []) + list(right or []):
        if item not in values:
            values.append(item)
    return values


def _merge_mailboxes(
    left: Optional[Dict[str, List[Dict[str, Any]]]],
    right: Optional[Dict[str, List[Dict[str, Any]]]],
) -> Dict[str, List[Dict[str, Any]]]:
    merged: Dict[str, List[Dict[str, Any]]] = {
        key: list(value)
        for key, value in dict(left or {}).items()
    }
    for key, values in dict(right or {}).items():
        merged.setdefault(key, [])
        merged[key].extend(list(values or []))
    return merged


def _take_latest_str(
    left: Optional[str],
    right: Optional[str],
) -> Optional[str]:
    return right if right is not None else left


class KernelHandoff(BaseModel):
    target_agent: str = Field(description="Which agent should receive control next.")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Typed handoff data that will later come from handoff tools.",
    )
    reason: Optional[str] = Field(default=None, description="Short explanation for the transfer.")


class KernelAgentResult(BaseModel):
    notes: Optional[str] = Field(default=None, description="Human-readable summary for terminal debugging.")
    updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Partial shared-state updates produced by the agent.",
    )
    handoff: Optional[KernelHandoff] = Field(
        default=None,
        description="If set, control is transferred to the target agent.",
    )


class SwarmKernelState(TypedDict, total=False):
    patient_context: Dict[str, Any]
    active_agent: Optional[str]
    handoff_inbox: Dict[str, List[Dict[str, Any]]]
    handoff_history: List[Dict[str, Any]]
    results: Dict[str, Dict[str, Any]]
    doctor_inputs: Dict[str, Dict[str, Any]]
    ready_sources: List[str]
    completed_agents: List[str]
    timeline: List[Dict[str, Any]]
    final_output: Optional[Dict[str, Any]]


class SwarmKernelGraphState(TypedDict):
    patient_context: Dict[str, Any]
    active_agent: Annotated[Optional[str], _take_latest_str]
    handoff_inbox: Annotated[Dict[str, List[Dict[str, Any]]], _merge_mailboxes]
    handoff_history: Annotated[List[Dict[str, Any]], operator.add]
    results: Annotated[Dict[str, Dict[str, Any]], _merge_dicts]
    doctor_inputs: Annotated[Dict[str, Dict[str, Any]], _merge_dicts]
    ready_sources: Annotated[List[str], _merge_unique_str_lists]
    completed_agents: Annotated[List[str], _merge_unique_str_lists]
    timeline: Annotated[List[Dict[str, Any]], operator.add]
    final_output: Optional[Dict[str, Any]]


AgentHandler = Callable[[SwarmKernelState], KernelAgentResult]


@dataclass(frozen=True)
class KernelAgentDefinition:
    name: str
    handler: AgentHandler
    final_source: Optional[str] = None
    is_final_agent: bool = False
    description: Optional[str] = None


@dataclass
class SwarmKernel:
    start_agents: Tuple[str, ...]
    final_agent: str
    required_final_sources: Tuple[str, ...]
    agents: Dict[str, KernelAgentDefinition] = field(default_factory=dict)

    def register_agent(
        self,
        *,
        name: str,
        handler: AgentHandler,
        final_source: Optional[str] = None,
        is_final_agent: bool = False,
        description: Optional[str] = None,
    ) -> None:
        self.agents[name] = KernelAgentDefinition(
            name=name,
            handler=handler,
            final_source=final_source,
            is_final_agent=is_final_agent,
            description=description,
        )

    def build(self):
        missing = [name for name in self.start_agents + (self.final_agent,) if name not in self.agents]
        if missing:
            raise ValueError(f"Kernel references unknown agents: {missing}")

        graph = StateGraph(SwarmKernelGraphState)
        graph.add_node("bootstrap", self._bootstrap)
        graph.add_node("doctor_gate", self._doctor_gate)

        for definition in self.agents.values():
            graph.add_node(definition.name, self._make_agent_node(definition))

        graph.add_edge(START, "bootstrap")
        graph.add_conditional_edges("bootstrap", self._route_bootstrap)
        graph.add_conditional_edges("doctor_gate", self._route_doctor_gate)

        return graph.compile()

    def initial_state(self, patient_context: Dict[str, Any]) -> SwarmKernelGraphState:
        return {
            "patient_context": dict(patient_context),
            "active_agent": None,
            "handoff_inbox": {},
            "handoff_history": [],
            "results": {},
            "doctor_inputs": {},
            "ready_sources": [],
            "completed_agents": [],
            "timeline": [],
            "final_output": None,
        }

    def _bootstrap(self, state: SwarmKernelGraphState) -> dict[str, Any]:
        return {
            "timeline": [
                {
                    "event": "kernel_bootstrap",
                    "start_agents": list(self.start_agents),
                }
            ]
        }

    def _route_bootstrap(self, state: SwarmKernelGraphState) -> list[str]:
        return list(self.start_agents)

    def _doctor_gate(self, state: SwarmKernelGraphState) -> dict[str, Any]:
        ready_sources = set(state.get("ready_sources") or [])
        missing = [name for name in self.required_final_sources if name not in ready_sources]
        return {
            "timeline": [
                {
                    "event": "doctor_gate_check",
                    "ready_sources": sorted(ready_sources),
                    "missing_sources": missing,
                }
            ]
        }

    def _route_doctor_gate(self, state: SwarmKernelGraphState) -> str:
        if state.get("final_output") is not None:
            return END

        ready_sources = set(state.get("ready_sources") or [])
        if all(name in ready_sources for name in self.required_final_sources):
            return self.final_agent
        return END

    def _make_agent_node(
        self,
        definition: KernelAgentDefinition,
    ) -> Callable[[SwarmKernelGraphState], Command[str]]:
        def _node(state: SwarmKernelGraphState) -> Command[str]:
            snapshot: SwarmKernelState = {
                "patient_context": dict(state.get("patient_context") or {}),
                "active_agent": definition.name,
                "handoff_inbox": {
                    key: list(value)
                    for key, value in dict(state.get("handoff_inbox") or {}).items()
                },
                "handoff_history": list(state.get("handoff_history") or []),
                "results": dict(state.get("results") or {}),
                "doctor_inputs": dict(state.get("doctor_inputs") or {}),
                "ready_sources": list(state.get("ready_sources") or []),
                "completed_agents": list(state.get("completed_agents") or []),
                "timeline": list(state.get("timeline") or []),
                "final_output": state.get("final_output"),
            }
            result = definition.handler(snapshot)

            updates: dict[str, Any] = {
                "active_agent": definition.name,
                "results": {
                    definition.name: {
                        "notes": result.notes,
                        **dict(result.updates or {}),
                    }
                },
                "completed_agents": [definition.name],
                "timeline": [
                    {
                        "event": "agent_executed",
                        "agent": definition.name,
                        "notes": result.notes,
                    }
                ],
            }

            if result.updates:
                updates.update(dict(result.updates))

            if definition.is_final_agent:
                final_output = dict(result.updates.get("final_output") or state.get("final_output") or {})
                updates["final_output"] = final_output
                updates["timeline"].append(
                    {
                        "event": "final_output_created",
                        "agent": definition.name,
                    }
                )
                return Command(goto=END, update=updates)

            handoff = result.handoff
            if handoff is None:
                updates["timeline"].append(
                    {
                        "event": "agent_stopped_without_handoff",
                        "agent": definition.name,
                    }
                )
                return Command(goto=END, update=updates)

            if handoff.target_agent not in self.agents:
                raise ValueError(
                    f"Agent '{definition.name}' attempted handoff to unknown agent '{handoff.target_agent}'."
                )

            inbox_update = {
                handoff.target_agent: [
                    {
                        "from_agent": definition.name,
                        "payload": dict(handoff.payload),
                        "reason": handoff.reason,
                    }
                ]
            }
            updates["handoff_inbox"] = inbox_update
            updates["handoff_history"] = [
                {
                    "from_agent": definition.name,
                    "to_agent": handoff.target_agent,
                    "reason": handoff.reason,
                    "payload": dict(handoff.payload),
                }
            ]
            updates["timeline"].append(
                {
                    "event": "handoff_requested",
                    "from_agent": definition.name,
                    "to_agent": handoff.target_agent,
                    "reason": handoff.reason,
                }
            )

            if handoff.target_agent == self.final_agent and definition.final_source:
                updates["doctor_inputs"] = {definition.final_source: dict(handoff.payload)}
                updates["ready_sources"] = [definition.final_source]
                return Command(goto="doctor_gate", update=updates)

            return Command(goto=handoff.target_agent, update=updates)

        return _node


def build_demo_kernel() -> SwarmKernel:
    kernel = SwarmKernel(
        start_agents=("esi1_agent", "vitals_agent"),
        final_agent="doctor_agent",
        required_final_sources=("acuity", "vitals"),
    )

    def esi1_agent(state: SwarmKernelState) -> KernelAgentResult:
        patient = state["patient_context"]
        if patient.get("needs_immediate_lifesaving_intervention"):
            return KernelAgentResult(
                notes="ESI-1 threshold met, escalating directly to doctor.",
                handoff=KernelHandoff(
                    target_agent="doctor_agent",
                    reason="Immediate life-saving intervention suspected.",
                    payload={
                        "path": ["esi1_agent"],
                        "recommended_esi": 1,
                        "summary": "Immediate intervention criteria met.",
                    },
                ),
            )

        return KernelAgentResult(
            notes="ESI-1 not met, handing off to ESI-2.",
            handoff=KernelHandoff(
                target_agent="esi2_agent",
                reason="Requires lower-acuity specialist review.",
                payload={
                    "path": ["esi1_agent", "esi2_agent"],
                    "screened_out_of_esi1": True,
                },
            ),
        )

    def esi2_agent(state: SwarmKernelState) -> KernelAgentResult:
        patient = state["patient_context"]
        if patient.get("high_risk_situation"):
            return KernelAgentResult(
                notes="High risk detected, escalating to doctor as ESI-2.",
                handoff=KernelHandoff(
                    target_agent="doctor_agent",
                    reason="High-risk situation or severe pain/distress.",
                    payload={
                        "path": ["esi1_agent", "esi2_agent"],
                        "recommended_esi": 2,
                        "summary": "High risk marker detected during ESI-2 review.",
                    },
                ),
            )

        return KernelAgentResult(
            notes="ESI-2 not met, handing off to ESI-3/4/5 predictor.",
            handoff=KernelHandoff(
                target_agent="esi345_agent",
                reason="Resource prediction required.",
                payload={
                    "path": ["esi1_agent", "esi2_agent", "esi345_agent"],
                    "screened_out_of_esi2": True,
                },
            ),
        )

    def esi345_agent(state: SwarmKernelState) -> KernelAgentResult:
        patient = state["patient_context"]
        predicted_esi = int(patient.get("predicted_esi", 3))
        return KernelAgentResult(
            notes=f"Predicted final branch acuity ESI-{predicted_esi}, handing to doctor.",
            handoff=KernelHandoff(
                target_agent="doctor_agent",
                reason="Acuity branch complete.",
                payload={
                    "path": ["esi1_agent", "esi2_agent", "esi345_agent"],
                    "recommended_esi": predicted_esi,
                    "summary": f"Resource predictor suggests ESI-{predicted_esi}.",
                },
            ),
        )

    def vitals_agent(state: SwarmKernelState) -> KernelAgentResult:
        patient = state["patient_context"]
        return KernelAgentResult(
            notes="Vitals interpreted and forwarded to doctor.",
            handoff=KernelHandoff(
                target_agent="doctor_agent",
                reason="Vitals branch complete.",
                payload={
                    "shock_index": patient.get("shock_index"),
                    "danger_zone_flag": bool(patient.get("danger_zone_flag")),
                    "summary": "Vitals review complete.",
                },
            ),
        )

    def doctor_agent(state: SwarmKernelState) -> KernelAgentResult:
        doctor_inputs = dict(state.get("doctor_inputs") or {})
        acuity = dict(doctor_inputs.get("acuity") or {})
        vitals = dict(doctor_inputs.get("vitals") or {})
        danger_zone = bool(vitals.get("danger_zone_flag"))
        recommended_esi = int(acuity.get("recommended_esi", 3))
        final_esi = 1 if danger_zone else recommended_esi
        return KernelAgentResult(
            notes="Doctor merged acuity and vitals into a final review.",
            updates={
                "final_output": {
                    "final_esi": final_esi,
                    "acuity_summary": acuity.get("summary"),
                    "vitals_summary": vitals.get("summary"),
                    "shock_index": vitals.get("shock_index"),
                    "acuity_path": acuity.get("path", []),
                    "danger_zone_override": danger_zone,
                }
            },
        )

    kernel.register_agent(
        name="esi1_agent",
        handler=esi1_agent,
        final_source="acuity",
        description="Initial ESI-1 screener.",
    )
    kernel.register_agent(
        name="esi2_agent",
        handler=esi2_agent,
        final_source="acuity",
        description="ESI-2 screener.",
    )
    kernel.register_agent(
        name="esi345_agent",
        handler=esi345_agent,
        final_source="acuity",
        description="ESI-3/4/5 resource predictor.",
    )
    kernel.register_agent(
        name="vitals_agent",
        handler=vitals_agent,
        final_source="vitals",
        description="Vitals-only review branch.",
    )
    kernel.register_agent(
        name="doctor_agent",
        handler=doctor_agent,
        is_final_agent=True,
        description="Supervisor/final reviewer.",
    )
    return kernel


def _print_demo_result(title: str, result: SwarmKernelGraphState) -> None:
    print(f"\n=== {title} ===")
    print("Timeline:")
    for event in result.get("timeline", []):
        print(f" - {event}")
    print("Handoffs:")
    for handoff in result.get("handoff_history", []):
        print(f" - {handoff}")
    print("Doctor Inputs:")
    print(result.get("doctor_inputs"))
    print("Final Output:")
    print(result.get("final_output"))


def main() -> None:
    kernel = build_demo_kernel()
    app = kernel.build()

    direct_case = app.invoke(
        kernel.initial_state(
            {
                "needs_immediate_lifesaving_intervention": True,
                "danger_zone_flag": False,
                "shock_index": 0.82,
            }
        )
    )
    _print_demo_result("Direct Doctor Handoff", direct_case)

    escalated_case = app.invoke(
        kernel.initial_state(
            {
                "needs_immediate_lifesaving_intervention": False,
                "high_risk_situation": False,
                "predicted_esi": 3,
                "danger_zone_flag": True,
                "shock_index": 1.14,
            }
        )
    )
    _print_demo_result("ESI345 Plus Vitals Override", escalated_case)


if __name__ == "__main__":
    main()
