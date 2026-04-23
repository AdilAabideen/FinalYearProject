from __future__ import annotations

from typing import Any, Dict

from app.agentic.swarm_contract import SwarmState


def build_payload(state: SwarmState) -> Dict[str, Any]:
    """Build a compact ESI2 swarm payload."""
    pending_handoff = dict(state.get("pending_handoff") or {})
    handoff_payload = dict(pending_handoff.get("payload") or {})
    llm_payload = {
        "task": "Evaluate this patient for ESI Decision Point B only.",
        "agent_role": "esi2_agent",
        "case_info": dict(state.get("case_info") or {}),
        "handoff_context": (
            "You are receiving a handoff from the ESI1 Agent. "
            "This means the patient was judged to be NOT ESI-1."
            "Use this as Prior Context"
        ),
        "prior_agent": pending_handoff.get("from_agent"),
        "prior_result": handoff_payload,
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
