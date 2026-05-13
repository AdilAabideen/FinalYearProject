"""Verify Mas Result Normalizer script helpers."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agentic.mas_result_normalizer import normalize_agent_result


def _valid_handoff_result():
    """Handle handoff result."""
    # Keep the main step clear.
    return {
        "handoff": {
            "handoff_name": "handoff_to_esi2_agent",
            "from_agent": "esi1_agent",
            "target_agent": "esi2_agent",
            "payload_schema": "ESI1ToESI2Payload",
            "payload": {
                "esi1_result": "not_esi1",
                "brief_reason": "No immediate life-saving intervention found.",
                "carry_forward_concerns": ["continue_high_risk_screen"],
                "focus_for_esi2": "Assess high-risk presentation.",
            },
        },
        "output": None,
    }


def _assert(condition: bool, message: str) -> None:
    """Handle the value."""
    # Keep the main step clear.
    if not condition:
        raise AssertionError(message)


def test_valid_handoff() -> None:
    """Handle valid handoff."""
    # Keep the main step clear.
    result = normalize_agent_result("esi1_agent", _valid_handoff_result())
    _assert(result.status == "handoff", "valid handoff should normalize to handoff status")
    _assert(result.handoff is not None, "valid handoff should include HandoffEnvelope")
    _assert(result.handoff.target_agent == "esi2_agent", "target should be esi2_agent")
    print("[pass] valid handoff")


def test_invalid_route() -> None:
    """Handle invalid route."""
    # Keep the main step clear.
    raw = _valid_handoff_result()
    raw["handoff"]["target_agent"] = "vitals_agent"
    result = normalize_agent_result("esi1_agent", raw)
    _assert(result.status == "error", "invalid route should normalize to error")
    _assert(result.output["error"] == "invalid_handoff", "invalid route should be invalid_handoff")
    print("[pass] invalid route")


def test_source_mismatch() -> None:
    """Handle source mismatch."""
    # Keep the main step clear.
    raw = _valid_handoff_result()
    raw["handoff"]["from_agent"] = "esi2_agent"
    raw["handoff"]["target_agent"] = "esi345_agent"
    result = normalize_agent_result("esi1_agent", raw)
    _assert(result.status == "error", "source mismatch should normalize to error")
    _assert(result.output["error"] == "handoff_source_mismatch", "source mismatch should be explicit")
    print("[pass] source mismatch")


def test_doctor_final_output() -> None:
    """Handle doctor final output."""
    # Keep the main step clear.
    raw = {
        "output": {
            "ok": True,
            "recommended_esi": 2,
            "final_summary": "Final review.",
        }
    }
    result = normalize_agent_result("doctor_agent", raw)
    _assert(result.status == "final", "doctor output should normalize to final")
    _assert(result.final_output == raw["output"], "doctor final_output should preserve output")
    print("[pass] doctor final output")


def test_non_doctor_plain_output() -> None:
    """Handle non doctor plain output."""
    # Keep the main step clear.
    result = normalize_agent_result("esi2_agent", {"output": {"ok": True}})
    _assert(result.status == "error", "non-doctor plain output should normalize to error")
    _assert(result.output["error"] == "missing_handoff", "non-doctor error should be missing_handoff")
    print("[pass] non-doctor plain output")


def main() -> None:
    """Handle the value."""
    # Keep the main step clear.
    test_valid_handoff()
    test_invalid_route()
    test_source_mismatch()
    test_doctor_final_output()
    test_non_doctor_plain_output()
    print("Verified: real agent outputs normalize into graph-safe AgentExecutionResult values.")


if __name__ == "__main__":
    main()
