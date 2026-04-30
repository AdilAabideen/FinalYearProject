from __future__ import annotations

from typing import Any, Dict

from app.agentic.swarm_contract import SwarmState
from app.agentic.workflows.definitions.esi_swarm_v1.payload_builders import (
    unified_payload_builder,
)


def build_payload(state: SwarmState) -> Dict[str, Any]:
    """Build a compact ESI1 swarm payload."""
    case_info = unified_payload_builder("esi1_agent", dict(state.get("case_info") or {}))
    llm_payload = {
        "task": "Evaluate this patient for ESI Decision Point A only.",
        "agent_role": "esi1_agent",
        "case_info": case_info,
        "handoff_context": None,
    }
    return {
        "llm_payload": llm_payload,
        "metadata": {
            "agent_role": "esi1_agent",
            "uses_handoff": False,
        },
    }
