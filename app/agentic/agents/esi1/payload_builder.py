from __future__ import annotations

from typing import Any, Dict

from app.agentic.swarm_contract import SwarmState


def build_payload(state: SwarmState) -> Dict[str, Any]:
    """Build a compact ESI1 swarm payload."""
    llm_payload = {
        "task": "Evaluate this patient for ESI Decision Point A only.",
        "agent_role": "esi1_agent",
        "case_info": dict(state.get("case_info") or {}),
        "handoff_context": None,
    }
    return {
        "llm_payload": llm_payload,
        "metadata": {
            "agent_role": "esi1_agent",
            "uses_handoff": False,
        },
    }
