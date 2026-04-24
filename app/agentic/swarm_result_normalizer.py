# swarm_result_normalizer
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from pydantic import BaseModel

from app.agentic.swarm_contract import (
    AgentExecutionResult,
    AgentName,
    HandoffEnvelope,
    agent_can_finalize,
)


def _to_plain_dict(value: Any) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Mapping):
        return dict(value)
    return None


def _extract_handoff(raw_result: Any) -> Optional[Any]:
    raw_dict = _to_plain_dict(raw_result)
    if raw_dict is None:
        return None
    return raw_dict.get("handoff")


def _extract_output(raw_result: Any) -> Optional[Dict[str, Any]]:
    raw_dict = _to_plain_dict(raw_result)
    if raw_dict is None:
        return None

    output = raw_dict.get("output")
    output_dict = _to_plain_dict(output)
    if output_dict is not None:
        return output_dict

    if "output" in raw_dict and output is None:
        return None

    if "handoff" in raw_dict:
        without_handoff = {key: value for key, value in raw_dict.items() if key != "handoff"}
        return without_handoff or None

    return raw_dict


def _error_result(
    agent_name: AgentName,
    *,
    error: str,
    details: Optional[str] = None,
    raw_result: Any = None,
) -> AgentExecutionResult:
    output: Dict[str, Any] = {"error": error}
    if details:
        output["details"] = details
    raw_dict = _to_plain_dict(raw_result)
    if raw_dict is not None:
        output["raw_result"] = raw_dict
    elif raw_result is not None:
        output["raw_result_repr"] = repr(raw_result)

    return AgentExecutionResult(
        agent_name=agent_name,
        status="error",
        output=output,
    )


def normalize_agent_result(agent_name: AgentName, raw_result: Any) -> AgentExecutionResult:
    """Convert raw real-agent output into the graph execution contract."""
    handoff_raw = _extract_handoff(raw_result)
    if handoff_raw is not None:
        try:
            handoff = HandoffEnvelope.model_validate(handoff_raw)
        except Exception as exc:
            return _error_result(
                agent_name,
                error="invalid_handoff",
                details=str(exc),
                raw_result=raw_result,
            )

        if handoff.from_agent != agent_name:
            return _error_result(
                agent_name,
                error="handoff_source_mismatch",
                details="Handoff source '{source}' does not match active agent '{agent}'.".format(
                    source=handoff.from_agent,
                    agent=agent_name,
                ),
                raw_result=raw_result,
            )

        return AgentExecutionResult(
            agent_name=agent_name,
            status="handoff",
            output={
                "raw_output": _extract_output(raw_result),
                "handoff_name": handoff.handoff_name,
                "target_agent": handoff.target_agent,
            },
            handoff=handoff,
        )

    final_output = _extract_output(raw_result)
    if agent_can_finalize(agent_name):
        if final_output is None:
            return _error_result(
                agent_name,
                error="missing_final_output",
                raw_result=raw_result,
            )
        return AgentExecutionResult(
            agent_name=agent_name,
            status="final",
            output=final_output,
            final_output=final_output,
        )

    return _error_result(
        agent_name,
        error="missing_handoff",
        details="Non-finalizing agents must return a handoff in swarm mode.",
        raw_result=raw_result,
    )
