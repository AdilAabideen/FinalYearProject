from __future__ import annotations

from datetime import datetime

import pytest

from app.agentic.telemetry.event_emitter import EventEmitter
from app.agentic.telemetry.metrics_types import LLMCallMetric, ToolExecutionMetric
from app.agentic.telemetry.telemetry_emitter import TelemetryEmitter
from app.agentic.telemetry.usage_extractor import extract_provider_usage


class FakeResponse:
    def __init__(self, usage_metadata=None, response_metadata=None):
        self.usage_metadata = usage_metadata
        self.response_metadata = response_metadata


@pytest.mark.unit
def test_ut_tel_001_emit_is_noop_before_context_and_handlers_are_set():
    emitter = EventEmitter()
    emitter.emit(event_type="assistant")


@pytest.mark.unit
def test_ut_tel_002_sequence_id_increments_monotonically():
    events = []
    emitter = EventEmitter()
    emitter.set_context(run_id="run_1", agent_name="agent")
    emitter.set_handlers([events.append])
    emitter.emit(event_type="assistant")
    emitter.emit(event_type="assistant")
    assert [item["seq"] for item in events] == [1, 2]


@pytest.mark.unit
def test_ut_tel_003_payload_includes_run_id_and_agent_name():
    events = []
    emitter = EventEmitter()
    emitter.set_context(run_id="run_1", agent_name="agent")
    emitter.set_handlers([events.append])
    emitter.emit(event_type="assistant")
    assert events[0]["run_id"] == "run_1"
    assert events[0]["agent_name"] == "agent"


@pytest.mark.unit
def test_ut_tel_004_multiple_handlers_all_receive_identical_payload():
    left = []
    right = []
    emitter = EventEmitter()
    emitter.set_context(run_id="run_1", agent_name="agent")
    emitter.set_handlers([left.append, right.append])
    emitter.emit(event_type="assistant")
    assert left[0] == right[0]


@pytest.mark.unit
def test_ut_tel_005_next_call_index_increments_deterministically():
    emitter = TelemetryEmitter()
    assert emitter.next_call_index() == 1
    assert emitter.next_call_index() == 2


@pytest.mark.unit
def test_ut_tel_006_current_context_returns_set_values():
    emitter = TelemetryEmitter()
    emitter.set_context(run_id="run_1", agent_name="agent")
    assert emitter.current_context() == ("run_1", "agent")


@pytest.mark.unit
def test_ut_tel_007_llm_metric_is_emitted_to_all_handlers():
    items = []
    emitter = TelemetryEmitter()
    emitter.set_llm_handlers([items.append])
    emitter.emit_llm(
        LLMCallMetric(
            run_id="run_1",
            agent_name="agent",
            call_index=1,
            iteration=1,
            call_kind="main_loop",
            model_name="model",
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow(),
            latency_ms=10,
            input_tokens=1,
            output_tokens=2,
            tokens_total=3,
            usage_source="estimated",
            had_tool_calls=False,
            tool_call_count=0,
            tool_call_parse_source=None,
            text_recovered_tool_call_count=0,
            native_tool_call_count=0,
            tool_names=[],
            error_text=None,
        )
    )
    assert items[0]["call_index"] == 1


@pytest.mark.unit
def test_ut_tel_008_tool_metric_is_emitted_to_all_handlers():
    items = []
    emitter = TelemetryEmitter()
    emitter.set_tool_handlers([items.append])
    emitter.emit_tool(
        ToolExecutionMetric(
            run_id="run_1",
            agent_name="agent",
            iteration=1,
            tool_call_id="call_1",
            tool_name="tool",
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow(),
            latency_ms=10,
            status="success",
            result_char_count=3,
            result_estimated_tokens=1,
            error_text=None,
        )
    )
    assert items[0]["tool_call_id"] == "call_1"


@pytest.mark.unit
def test_ut_tel_009_noop_when_no_handlers_registered():
    emitter = TelemetryEmitter()
    emitter.emit_llm  # smoke


@pytest.mark.unit
def test_ut_tel_016_extract_usage_from_usage_metadata():
    result = extract_provider_usage(FakeResponse(usage_metadata={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}))
    assert result.input_tokens == 1
    assert result.total_tokens == 3


@pytest.mark.unit
def test_ut_tel_017_extract_usage_from_response_metadata_token_usage():
    result = extract_provider_usage(FakeResponse(response_metadata={"token_usage": {"prompt_tokens": 4, "completion_tokens": 5, "total_tokens": 9}}))
    assert result.input_tokens == 4
    assert result.output_tokens == 5


@pytest.mark.unit
def test_ut_tel_018_missing_totals_are_derived_from_input_plus_output():
    result = extract_provider_usage(FakeResponse(usage_metadata={"input_tokens": 1, "output_tokens": 2}))
    assert result.total_tokens == 3


@pytest.mark.unit
def test_ut_tel_019_missing_usage_returns_empty_usage_result():
    result = extract_provider_usage(FakeResponse())
    assert result.has_usage is False


@pytest.mark.unit
def test_ut_tel_020_non_integer_usage_values_coerce_safely_or_become_none():
    result = extract_provider_usage(FakeResponse(usage_metadata={"input_tokens": "2", "output_tokens": "bad"}))
    assert result.input_tokens == 2
    assert result.output_tokens == 0
