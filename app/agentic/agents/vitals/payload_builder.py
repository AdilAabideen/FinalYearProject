from __future__ import annotations

from typing import Any, Dict

from app.agentic.mas_contract import MASState
from app.agentic.workflows.definitions.esi_mas.payload_builders import (
    unified_payload_builder,
)


def build_payload(state: MASState) -> Dict[str, Any]:
    """Build a compact vitals mas payload."""
    case_info = unified_payload_builder("vitals_agent", dict(state.get("case_info") or {}))
    llm_payload = {
        "task": "Evaluate this patient for vitals-only up-triage concerns.",
        "agent_role": "vitals_agent",
        "case_info": case_info,
        "handoff_context": None,
    }
    return {
        "llm_payload": llm_payload,
        "metadata": {
            "agent_role": "vitals_agent",
            "uses_handoff": False,
        },
    }
