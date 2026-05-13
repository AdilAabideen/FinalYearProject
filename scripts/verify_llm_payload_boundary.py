from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agentic.HandRolledAgent import SSEHandrolledAgent
from app.agentic.agents.doctor.payload_builder import build_payload as build_doctor_payload
from app.agentic.agents.esi2.payload_builder import build_payload as build_esi2_payload
from app.agentic.mas_contract import MASState, make_initial_mas_state


def _state_with_handoffs() -> MASState:
    state = make_initial_mas_state(
        {
            "chief_complaint": "Chest pain and dizziness",
            "age": 72,
            "heart_rate": 128,
            "systolic_bp": 88,
        }
    )
    esi1_to_esi2 = {
        "handoff_name": "handoff_to_esi2_agent",
        "from_agent": "esi1_agent",
        "target_agent": "esi2_agent",
        "payload_schema": "ESI1ToESI2Payload",
        "payload": {
            "esi1_result": "not_esi1",
            "brief_reason": "No immediate life-saving intervention identified.",
            "carry_forward_concerns": ["continue_high_risk_screen"],
        },
    }
    vitals_to_doctor = {
        "handoff_name": "handoff_to_doctor_agent",
        "from_agent": "vitals_agent",
        "target_agent": "doctor_agent",
        "payload_schema": "VitalsToDoctorPayload",
        "payload": {
            "consider_uptriage": True,
            "abnormal_vitals": ["tachycardia", "hypotension"],
        },
    }
    esi345_to_doctor = {
        "handoff_name": "handoff_to_doctor_agent",
        "from_agent": "esi345_agent",
        "target_agent": "doctor_agent",
        "payload_schema": "ESI345ToDoctorPayload",
        "payload": {
            "esi_level": 3,
            "num_resources": 2,
            "predicted_resources": ["labs", "CT"],
        },
    }
    state["pending_handoff"] = esi1_to_esi2
    state["handoff_history"] = [esi1_to_esi2, vitals_to_doctor, esi345_to_doctor]
    return state


def _assert_only_llm_payload_is_visible(name: str, payload: Dict[str, Any]) -> None:
    human_content = SSEHandrolledAgent._payload_to_human_content(payload)
    visible = json.loads(human_content)

    if visible != payload["llm_payload"]:
        raise AssertionError(
            "{name}: human content did not exactly match llm_payload.\nVisible: {visible}\nExpected: {expected}".format(
                name=name,
                visible=visible,
                expected=payload["llm_payload"],
            )
        )

    raw_content = human_content.lower()
    forbidden_terms = ("metadata", "uses_handoff", "handoff_name", "doctor_handoff_count")
    leaked_terms = [term for term in forbidden_terms if term in raw_content]
    if leaked_terms:
        raise AssertionError(
            "{name}: metadata leaked into human content: {terms}".format(
                name=name,
                terms=", ".join(leaked_terms),
            )
        )

    print("[pass] {name}".format(name=name))
    print(human_content)
    print()


def main() -> None:
    state = _state_with_handoffs()
    checks = {
        "esi2_payload": build_esi2_payload(state),
        "doctor_payload": build_doctor_payload(state),
    }

    for name, payload in checks.items():
        _assert_only_llm_payload_is_visible(name, payload)

    print("Verified: _payload_to_human_content serializes only llm_payload from wrapped mas payloads.")


if __name__ == "__main__":
    main()
