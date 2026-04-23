from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.agentic.telemetry.token_estimator import TokenEstimator


@pytest.mark.unit
def test_ut_tel_010_empty_text_returns_zero_tokens():
    assert TokenEstimator().estimate_text_tokens("") == 0


@pytest.mark.unit
def test_ut_tel_011_fallback_estimator_returns_positive_value_for_non_empty_text():
    estimator = TokenEstimator(chars_per_token_fallback=4)
    estimator._encoder_checked = True
    estimator._encoder = None
    assert estimator.estimate_text_tokens("abcd") == 1


@pytest.mark.unit
def test_ut_tel_012_message_serialization_is_deterministic_for_same_input():
    estimator = TokenEstimator()
    msg = AIMessage(content="hello")
    assert estimator.serialize_message_for_estimation(msg) == estimator.serialize_message_for_estimation(msg)


@pytest.mark.unit
def test_ut_tel_013_ai_output_serialization_includes_tool_calls():
    estimator = TokenEstimator()
    msg = AIMessage(content="", tool_calls=[{"id": "call_1", "name": "tool_a", "args": {"x": 1}}])
    assert '"tool_calls"' in estimator.serialize_ai_output_for_estimation(msg)


@pytest.mark.unit
def test_ut_tel_014_tool_call_string_arguments_are_normalized_in_token_serialization():
    estimator = TokenEstimator()
    msg = AIMessage(
        content="",
        additional_kwargs={"tool_calls": [{"id": "call_1", "function": {"name": "tool_a", "arguments": "{\"x\": 1}"}}]},
    )
    serialized = estimator.serialize_ai_output_for_estimation(msg)
    assert '"provider_tool_calls"' in serialized
    assert '"x":1' in serialized


@pytest.mark.unit
def test_ut_tel_015_tool_messages_include_tool_metadata_in_serialization():
    estimator = TokenEstimator()
    serialized = estimator.serialize_message_for_estimation(
        ToolMessage(content="done", tool_call_id="call_1", name="tool_a", status="success")
    )
    assert '"tool_call_id":"call_1"' in serialized
    assert '"status":"success"' in serialized
