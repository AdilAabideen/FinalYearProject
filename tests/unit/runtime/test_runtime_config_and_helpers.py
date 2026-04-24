from __future__ import annotations

import pytest

from app.agentic.HandRolledAgent import SSEHandrolledAgent
from app.agentic.runtime.failure_taxonomy import FailureCategory
from app.agentic.runtime.runtime_config import RuntimeConfig


@pytest.mark.unit
def test_ut_run_028_runtime_config_rejects_max_tool_calls_per_turn_below_one():
    with pytest.raises(ValueError):
        RuntimeConfig(max_tool_calls_per_turn=0)


@pytest.mark.unit
def test_ut_run_029_runtime_config_rejects_negative_malformed_retry_count():
    with pytest.raises(ValueError):
        RuntimeConfig(max_malformed_tool_retries=-1)


@pytest.mark.unit
def test_ut_run_030_failure_taxonomy_values_remain_stable():
    assert FailureCategory.UNKNOWN_TOOL.value == "unknown_tool"
    assert FailureCategory.FINAL_OUTPUT_INVALID.value == "final_output_invalid"


@pytest.mark.unit
def test_ut_run_031_payload_to_human_content_extracts_plain_string_input():
    assert SSEHandrolledAgent._payload_to_human_content("hello") == "hello"


@pytest.mark.unit
def test_ut_run_033_payload_to_human_content_extracts_latest_user_message_from_dict_messages():
    payload = {"messages": [{"role": "user", "content": "first"}, {"role": "user", "content": "latest"}]}
    assert SSEHandrolledAgent._payload_to_human_content(payload) == "latest"


@pytest.mark.unit
def test_ut_run_034_limit_tool_calls_splits_kept_and_dropped_calls_correctly():
    agent = object.__new__(SSEHandrolledAgent)
    agent.max_tool_calls = 2
    kept, dropped = SSEHandrolledAgent._limit_tool_calls(
        agent,
        [
            {"id": "1"},
            {"id": "2"},
            {"id": "3"},
        ],
    )
    assert [item["id"] for item in kept] == ["1", "2"]
    assert [item["id"] for item in dropped] == ["3"]


@pytest.mark.unit
def test_ut_run_035_parsed_to_payload_json_wraps_scalar_values_under_value():
    assert SSEHandrolledAgent._parsed_to_payload_json("x") == {"value": "x"}
