#MAS Contract
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, FrozenSet, List, Literal, Optional, Tuple, TypedDict

from pydantic import BaseModel, Field, model_validator

from app.agentic.workflows.registry import get_workflow_definition


AgentName = Literal[
    "esi1_agent",
    "esi2_agent",
    "esi345_agent",
    "vitals_agent",
    "doctor_agent",
]

ExecutionStatus = Literal["handoff", "final", "error"]

_WORKFLOW = get_workflow_definition("esi_mas")


def merge_dicts(
    left: Optional[Dict[str, Any]],
    right: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(left or {})
    merged.update(right or {})
    return merged


def merge_unique_lists(
    left: Optional[List[str]],
    right: Optional[List[str]],
) -> List[str]:
    values: List[str] = []
    for item in list(left or []) + list(right or []):
        if item not in values:
            values.append(item)
    return values


def take_latest_str(
    left: Optional[str],
    right: Optional[str],
) -> Optional[str]:
    return right if right is not None else left


class HandoffEnvelope(BaseModel):
    handoff_name: str = Field(..., description="Stable handoff tool/result identifier.")
    from_agent: AgentName = Field(..., description="Agent initiating the handoff.")
    target_agent: AgentName = Field(..., description="Agent that should execute next.")
    payload_schema: str = Field(..., description="Schema name used to validate the handoff payload.")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Structured carry-forward payload.")

    @model_validator(mode="after")
    def validate_route(self) -> "HandoffEnvelope":
        allowed_targets = allowed_handoffs_for(self.from_agent)
        if self.target_agent not in allowed_targets:
            raise ValueError(
                "Invalid handoff route '{source}' -> '{target}'. Allowed targets: {allowed}.".format(
                    source=self.from_agent,
                    target=self.target_agent,
                    allowed=", ".join(sorted(allowed_targets)),
                )
            )
        return self


class AgentExecutionPayload(BaseModel):
    agent_name: AgentName = Field(..., description="Which agent should execute now.")
    case_info: Dict[str, Any] = Field(default_factory=dict, description="Original normalized case input.")
    active_handoff: Optional[HandoffEnvelope] = Field(
        default=None,
        description="Most recent handoff that routed execution to this agent.",
    )
    handoff_history: List[HandoffEnvelope] = Field(
        default_factory=list,
        description="Prior handoffs accumulated in the mas.",
    )


class AgentExecutionResult(BaseModel):
    agent_name: AgentName = Field(..., description="Which agent produced this execution result.")
    status: ExecutionStatus = Field(..., description="What the graph should do after this execution.")
    output: Dict[str, Any] = Field(default_factory=dict, description="Structured output from the agent.")
    handoff: Optional[HandoffEnvelope] = Field(
        default=None,
        description="Next-step handoff to another agent, when status='handoff'.",
    )
    final_output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Final mas output, only valid for finalizing agents.",
    )

    @model_validator(mode="after")
    def validate_contract(self) -> "AgentExecutionResult":
        if self.status == "handoff" and self.handoff is None:
            raise ValueError("status='handoff' requires a handoff envelope.")
        if self.status == "final":
            if not agent_can_finalize(self.agent_name):
                raise ValueError(
                    "Only finalizing agents may return status='final'. Got '{agent}'.".format(
                        agent=self.agent_name
                    )
                )
            if self.final_output is None:
                raise ValueError("status='final' requires final_output.")
        if self.status != "final" and self.final_output is not None:
            raise ValueError("final_output is only valid when status='final'.")
        return self


class MASState(TypedDict):
    case_info: Dict[str, Any]
    execution_context: Annotated[Optional[Dict[str, Any]], merge_dicts]
    active_agent: Annotated[Optional[str], take_latest_str]
    pending_handoff: Annotated[Optional[Dict[str, Any]], merge_dicts]
    pending_agent_payload: Annotated[Optional[Dict[str, Any]], merge_dicts]
    handoff_history: Annotated[List[Dict[str, Any]], operator.add]
    completed_agents: Annotated[List[str], merge_unique_lists]
    execution_trace: Annotated[List[Dict[str, Any]], operator.add]
    final_output: Annotated[Optional[Dict[str, Any]], merge_dicts]


finalizing_agents: FrozenSet[AgentName] = frozenset(_WORKFLOW.finalizing_agents)
handoff_tool_agents: FrozenSet[AgentName] = frozenset(
    agent_name
    for agent_name, targets in _WORKFLOW.allowed_handoffs.items()
    if len(targets) > 0
)
parallel_start_agents: Tuple[AgentName, ...] = _WORKFLOW.start_agents

allowed_handoffs: Dict[AgentName, FrozenSet[AgentName]] = {
    source_agent: frozenset(target_agents)
    for source_agent, target_agents in _WORKFLOW.allowed_handoffs.items()
}


def allowed_handoffs_for(agent_name: AgentName) -> FrozenSet[AgentName]:
    return allowed_handoffs.get(agent_name, frozenset())


def agent_can_finalize(agent_name: AgentName) -> bool:
    return agent_name in finalizing_agents


def agent_can_handoff(agent_name: AgentName) -> bool:
    return agent_name in handoff_tool_agents


def is_parallel_start_agent(agent_name: AgentName) -> bool:
    return agent_name in parallel_start_agents


def make_initial_mas_state(
    case_info: Dict[str, Any],
    execution_context: Optional[Dict[str, Any]] = None,
) -> MASState:
    return {
        "case_info": dict(case_info),
        "execution_context": dict(execution_context or {}),
        "active_agent": None,
        "pending_handoff": None,
        "pending_agent_payload": None,
        "handoff_history": [],
        "completed_agents": [],
        "execution_trace": [],
        "final_output": None,
    }
