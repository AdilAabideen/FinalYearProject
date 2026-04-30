from __future__ import annotations

from typing import Any, Dict

from app.agentic.swarm_contract import SwarmState
from app.agentic.workflows.definitions.esi_swarm_v1.payload_builders import (
    unified_payload_builder,
)

def clean_payload(payload):
    return {
        "Concerns" : payload.get("carry_forward_concerns")
    }


def build_payload(state: SwarmState) -> Dict[str, Any]:
    """Build a compact ESI2 swarm payload."""
    pending_handoff = dict(state.get("pending_handoff") or {})
    handoff_payload = dict(pending_handoff.get("payload") or {})
    case_info = unified_payload_builder("esi2_agent", dict(state.get("case_info") or {}))
    llm_payload = {
        "case_info": case_info,
        "handoff_context": (
            "You are receiving a Case from the ESI1 Agent. "
            "This means the patient was judged to be NOT ESI-1."
            "Use this as Context"
        ),
        "prior_result": clean_payload(handoff_payload),
    }
    return {
        "llm_payload": llm_payload,
        "metadata": {
            "agent_role": "esi2_agent",
            "uses_handoff": True,
            "handoff_name": pending_handoff.get("handoff_name"),
            "from_agent": pending_handoff.get("from_agent"),
        },
    }
