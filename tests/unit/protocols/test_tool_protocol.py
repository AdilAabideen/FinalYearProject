from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agentic.protocols.protocol_types import ToolCallParseSource
from app.agentic.protocols.tool_protocol import normalize_tool_calls_typed


@pytest.mark.unit
def test_ut_pro_001_normalize_openai_style_raw_tool_call():
    calls = normalize_tool_calls_typed(
        [{"id": "call_1", "function": {"name": "tool_a", "arguments": "{\"x\": 1}"}}],
        source=ToolCallParseSource.FUNCTION_CALL,
    )
    assert len(calls) == 1
    assert calls[0].name == "tool_a"
    assert calls[0].args == {"x": 1}
    assert calls[0].id == "call_1"
    assert calls[0].source == ToolCallParseSource.FUNCTION_CALL


@pytest.mark.unit
def test_ut_pro_002_normalize_plain_tool_call_shape():
    calls = normalize_tool_calls_typed([{"id": "call_2", "name": "tool_a", "arguments": {"x": 2}}])
    assert calls[0].args == {"x": 2}


@pytest.mark.unit
def test_ut_pro_003_normalize_args_alias_shape():
    calls = normalize_tool_calls_typed([{"id": "call_3", "name": "tool_a", "args": {"x": 3}}])
    assert calls[0].args == {"x": 3}


@pytest.mark.unit
def test_ut_pro_004_parse_string_arguments_into_dict():
    calls = normalize_tool_calls_typed([{"id": "call_4", "name": "tool_a", "arguments": "{\"x\": 4}"}])
    assert calls[0].args == {"x": 4}


@pytest.mark.unit
def test_ut_pro_005_wrap_scalar_argument_payload_into_input():
    calls = normalize_tool_calls_typed([{"id": "call_5", "name": "tool_a", "arguments": "[1, 2]"}])
    assert calls[0].args == {"input": [1, 2]}


@pytest.mark.unit
def test_ut_pro_006_invalid_json_argument_string_falls_back_safely():
    calls = normalize_tool_calls_typed([{"id": "call_6", "name": "tool_a", "arguments": "{bad"}])
    assert calls[0].args == {"input": "{bad"}


@pytest.mark.unit
def test_ut_pro_007_reject_tool_with_missing_name():
    assert normalize_tool_calls_typed([{"id": "call_7", "arguments": {"x": 1}}]) == []


@pytest.mark.unit
def test_ut_pro_008_reject_unknown_tool_when_allow_list_present():
    assert normalize_tool_calls_typed(
        [{"id": "call_8", "name": "bad_tool", "arguments": {}}],
        allowed_tool_names={"good_tool"},
    ) == []


@pytest.mark.unit
def test_ut_pro_009_preserve_allowed_tool_when_allow_list_present():
    calls = normalize_tool_calls_typed(
        [{"id": "call_9", "name": "good_tool", "arguments": {}}],
        allowed_tool_names={"good_tool"},
    )
    assert len(calls) == 1
    assert calls[0].name == "good_tool"


@pytest.mark.unit
def test_ut_pro_010_generate_id_when_missing():
    with patch("app.agentic.protocols.tool_protocol.uuid.uuid4") as mocked_uuid:
        mocked_uuid.return_value.hex = "abcdef1234567890"
        calls = normalize_tool_calls_typed([{"name": "tool_a", "arguments": {}}])
    assert calls[0].id == "call_abcdef123456"


@pytest.mark.unit
def test_ut_pro_011_deduplicate_repeated_ids():
    with patch("app.agentic.protocols.tool_protocol.uuid.uuid4") as mocked_uuid:
        mocked_uuid.return_value.hex = "deduped1234567890"
        calls = normalize_tool_calls_typed(
            [
                {"id": "call_dup", "name": "tool_a", "arguments": {}},
                {"id": "call_dup", "name": "tool_b", "arguments": {}},
            ]
    )
    assert calls[0].id == "call_dup"
    assert calls[1].id == "call_deduped12345"


@pytest.mark.unit
def test_ut_pro_012_preserve_source_metadata():
    calls = normalize_tool_calls_typed(
        [{"id": "call_12", "name": "tool_a", "arguments": {}}],
        source=ToolCallParseSource.TEXT_JSON,
        recovered=True,
    )
    assert calls[0].source == ToolCallParseSource.TEXT_JSON
    assert calls[0].recovered is True
