from __future__ import annotations

from typing import Any, Dict

from app.agentic.swarm_contract import SwarmState
from app.agentic.workflows.definitions.esi_swarm_v1.payload_builders import (
    unified_payload_builder,
)


def build_payload(state: SwarmState) -> Dict[str, Any]:
    """Build a compact ESI345 swarm payload."""
    pending_handoff = dict(state.get("pending_handoff") or {})
    handoff_payload = dict(pending_handoff.get("payload") or {})
    case_info = unified_payload_builder("esi345_agent", dict(state.get("case_info") or {}))
    llm_payload = {
        "task": "Evaluate this patient for ESI Decision Point C only.",
        "agent_role": "esi345_agent",
        "case_info": case_info,
        "handoff_context": (
            "You are receiving a handoff from the ESI2 Agent. "
            "This means the patient was judged to be NOT ESI-2."
            "Use this as Prior Context"
        ),
        "prior_agent": pending_handoff.get("from_agent"),
        "prior_result": handoff_payload,
    }
    return {
        "llm_payload": llm_payload,
        "metadata": {
            "agent_role": "esi345_agent",
            "uses_handoff": True,
            "handoff_name": pending_handoff.get("handoff_name"),
            "from_agent": pending_handoff.get("from_agent"),
        },
    }
