from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agentic.swarm_contract import SwarmState
from app.agentic.workflows.definitions.esi_swarm_v1.payload_builders import (
    unified_payload_builder,
)


ACUITY_AGENTS = {"esi1_agent", "esi2_agent", "esi345_agent"}


def _doctor_handoffs(state: SwarmState) -> List[Dict[str, Any]]:
    return [
        dict(item)
        for item in list(state.get("handoff_history") or [])
        if isinstance(item, dict) and item.get("target_agent") == "doctor_agent"
    ]


def _latest_handoff_from(
    handoffs: List[Dict[str, Any]],
    source_agents: set[str],
) -> Optional[Dict[str, Any]]:
    for item in reversed(handoffs):
        if item.get("from_agent") in source_agents:
            return item
    return None


def build_payload(state: SwarmState) -> Dict[str, Any]:
    """Build a compact doctor swarm payload."""
    doctor_handoffs = _doctor_handoffs(state)
    acuity_handoff = _latest_handoff_from(doctor_handoffs, ACUITY_AGENTS)
    vitals_handoff = _latest_handoff_from(doctor_handoffs, {"vitals_agent"})
    acuity_payload = dict((acuity_handoff or {}).get("payload") or {})
    vitals_payload = dict((vitals_handoff or {}).get("payload") or {})
    case_info = unified_payload_builder("doctor_agent", dict(state.get("case_info") or {}))

    llm_payload = {
        "case_info": case_info.get("tirage_case"),
        "handoff_context": (
            "You are receiving one acuity-branch handoff and one vitals-branch handoff. "
            "Use both to produce the final review."
        ),
        "acuity_context": {
            "from_agent": (acuity_handoff or {}).get("from_agent"),
            "result": acuity_payload,
        },
        "vitals_context": {
            "from_agent": (vitals_handoff or {}).get("from_agent"),
            "result": vitals_payload,
        }
    }
    return {
        "llm_payload": llm_payload,
        "metadata": {
            "agent_role": "doctor_agent",
            "uses_handoff": True,
            "doctor_handoff_count": len(doctor_handoffs),
            "acuity_from_agent": (acuity_handoff or {}).get("from_agent"),
            "vitals_from_agent": (vitals_handoff or {}).get("from_agent"),
        },
    }
