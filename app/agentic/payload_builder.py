from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.agentic.agents.doctor.payload_builder import build_payload as build_doctor_payload
from app.agentic.agents.esi1.payload_builder import build_payload as build_esi1_payload
from app.agentic.agents.esi2.payload_builder import build_payload as build_esi2_payload
from app.agentic.agents.esi345.payload_builder import build_payload as build_esi345_payload
from app.agentic.agents.vitals.payload_builder import build_payload as build_vitals_payload
from app.agentic.swarm_contract import AgentName, SwarmState


PayloadBuilder = Callable[[SwarmState], Dict[str, Any]]


payload_builders: Dict[AgentName, PayloadBuilder] = {
    "esi1_agent": build_esi1_payload,
    "esi2_agent": build_esi2_payload,
    "esi345_agent": build_esi345_payload,
    "vitals_agent": build_vitals_payload,
    "doctor_agent": build_doctor_payload,
}


def _latest_handoff_for_agent(agent_name: AgentName, state: SwarmState) -> Optional[Dict[str, Any]]:
    pending_handoff = state.get("pending_handoff")
    if isinstance(pending_handoff, dict) and pending_handoff.get("target_agent") == agent_name:
        return dict(pending_handoff)

    for item in reversed(list(state.get("handoff_history") or [])):
        if isinstance(item, dict) and item.get("target_agent") == agent_name:
            return dict(item)

    return None


def _state_for_agent(agent_name: AgentName, state: SwarmState) -> SwarmState:
    scoped_state = dict(state)
    scoped_state["pending_handoff"] = _latest_handoff_for_agent(agent_name, state)
    return scoped_state  # type: ignore[return-value]


def build_pending_agent_payload(agent_name: AgentName, state: SwarmState) -> Dict[str, Any]:
    """Build the runtime payload wrapper for the next agent execution.

    The returned dict keeps the model-visible `llm_payload` separate from
    runtime-only `metadata`.
    """
    try:
        builder = payload_builders[agent_name]
    except KeyError as exc:
        raise ValueError("No payload builder registered for agent '{agent}'.".format(agent=agent_name)) from exc

    payload = builder(_state_for_agent(agent_name, state))
    if not isinstance(payload, dict) or not isinstance(payload.get("llm_payload"), dict):
        raise ValueError(
            "Payload builder for agent '{agent}' must return a dict containing llm_payload.".format(
                agent=agent_name
            )
        )

    metadata = payload.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError(
            "Payload builder for agent '{agent}' returned non-dict metadata.".format(agent=agent_name)
        )

    return payload
