from __future__ import annotations

from typing import Any, Dict

from app.agentic.mas_contract import MASState
from app.agentic.workflows.definitions.esi_mas.payload_builders import (
    unified_payload_builder,
)

def clean_payload(payload):
    return {
        "carry_forward_concerns" : payload.get("carry_forward_concerns"),
        "brief_reason" : payload.get("reason")
    }


def build_payload(state: MASState) -> Dict[str, Any]:
    """Build a compact ESI345 mas payload."""
    pending_handoff = dict(state.get("pending_handoff") or {})
    handoff_payload = dict(pending_handoff.get("payload") or {})
    case_info = unified_payload_builder("esi345_agent", dict(state.get("case_info") or {}))
    print(case_info)
    llm_payload = {
        "case_info": case_info,
        "handoff_context": (
            "You are receiving a handoff from the ESI2 Agent. "
            "This means the patient was judged to be NOT ESI-2."
        ),
        "prior_agent": pending_handoff.get("from_agent"),
        "prior_result": clean_payload(handoff_payload),
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
