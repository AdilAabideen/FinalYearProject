from __future__ import annotations

import pytest

from app.agentic.protocols.tool_call_recovery import (
    recover_from_fenced_json_text,
    recover_from_jsonl_text,
    recover_from_partial_json_text,
    recover_from_raw_json_text,
    recover_from_tool_calls_array_text,
    recover_tool_calls_from_content,
)


@pytest.mark.unit
def test_ut_pro_013_recover_raw_json_object_containing_tool_calls():
    result = recover_from_raw_json_text('{"tool_calls":[{"id":"call_1","name":"tool_a","arguments":{"x":1}}]}')
    assert result.succeeded is True
    assert result.calls[0].name == "tool_a"


@pytest.mark.unit
def test_ut_pro_014_recover_raw_json_single_call_object():
    result = recover_from_raw_json_text('{"id":"call_2","name":"tool_a","arguments":{"x":2}}')
    assert result.succeeded is True
    assert len(result.calls) == 1


@pytest.mark.unit
def test_ut_pro_015_recover_fenced_json_block():
    result = recover_from_fenced_json_text('```{"tool_calls":[{"id":"call_3","name":"tool_a","arguments":{"x":3}}]}```')
    assert result.succeeded is True


@pytest.mark.unit
def test_ut_pro_016_recover_fenced_json_block_with_language_label():
    result = recover_from_fenced_json_text('```json\n{"tool_calls":[{"id":"call_4","name":"tool_a","arguments":{"x":4}}]}\n```')
    assert result.succeeded is True


@pytest.mark.unit
def test_ut_pro_017_recover_jsonl_with_multiple_valid_lines():
    result = recover_from_jsonl_text(
        '{"id":"call_5","name":"tool_a","arguments":{"x":5}}\n{"id":"call_6","name":"tool_b","arguments":{"x":6}}'
    )
    assert result.succeeded is True
    assert len(result.calls) == 2
    assert result.all_lines_parsed is True


@pytest.mark.unit
def test_ut_pro_018_recover_jsonl_with_mixed_valid_and_invalid_lines():
    result = recover_from_jsonl_text(
        '{"id":"call_7","name":"tool_a","arguments":{"x":7}}\nnot-json\n{"id":"call_8","name":"tool_b","arguments":{"x":8}}'
    )
    assert result.succeeded is True
    assert len(result.calls) == 2
    assert result.all_lines_parsed is False


@pytest.mark.unit
def test_ut_pro_019_recover_from_partial_json_with_trailing_garbage():
    result = recover_from_partial_json_text(
        '{"tool_calls":[{"id":"call_9","name":"tool_a","arguments":{"x":9}}]} trailing'
    )
    assert result.succeeded is True
    assert result.calls[0].id == "call_9"


@pytest.mark.unit
def test_ut_pro_020_recover_from_embedded_balanced_tool_calls_array():
    result = recover_from_tool_calls_array_text(
        'prefix "tool_calls": [{"id":"call_10","name":"tool_a","arguments":{"x":10}}] suffix'
    )
    assert result.succeeded is True
    assert result.calls[0].name == "tool_a"


@pytest.mark.unit
def test_ut_pro_021_empty_assistant_text_returns_empty_parse_result():
    result = recover_tool_calls_from_content("")
    assert result.succeeded is False
    assert result.calls == []


@pytest.mark.unit
def test_ut_pro_022_malformed_text_returns_no_tool_calls_without_exception():
    result = recover_tool_calls_from_content("not valid tool content")
    assert result.succeeded is False
    assert result.calls == []


@pytest.mark.unit
def test_ut_pro_023_recovery_respects_allowed_tool_names():
    result = recover_from_raw_json_text(
        '{"tool_calls":[{"id":"call_11","name":"blocked","arguments":{}}]}',
        allowed_tool_names={"allowed"},
    )
    assert result.succeeded is False
    assert result.calls == []
