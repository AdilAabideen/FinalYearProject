from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.agentic.runtime.short_term_memory import ShortTermMemory, ShortTermMemoryConfig


@pytest.mark.unit
def test_ut_run_019_append_assistant_tool_call_message_succeeds():
    short_term_memory = ShortTermMemory()
    msg = AIMessage(content="", tool_calls=[{"id": "call_1", "name": "tool_a", "args": {}}])
    short_term_memory.append_assistant_tool_call(msg)
    assert len(short_term_memory.messages()) == 1


@pytest.mark.unit
def test_ut_run_020_append_assistant_tool_call_without_tool_calls_raises_error():
    short_term_memory = ShortTermMemory()
    with pytest.raises(ValueError):
        short_term_memory.append_assistant_tool_call(AIMessage(content="no tools"))


@pytest.mark.unit
def test_ut_run_021_append_tool_result_clones_message_safely():
    short_term_memory = ShortTermMemory()
    msg = ToolMessage(content="done", tool_call_id="call_1", name="tool_a", status="success")
    cloned = short_term_memory.append_tool_result(msg)
    assert cloned is not msg
    assert cloned.content == "done"


@pytest.mark.unit
def test_ut_run_022_final_assistant_is_excluded_when_config_disables_it():
    short_term_memory = ShortTermMemory(
        config=ShortTermMemoryConfig(include_final_assistant_output=False)
    )
    assert short_term_memory.append_final_assistant(AIMessage(content="final")) is None


@pytest.mark.unit
def test_ut_run_024_raw_provider_debug_keys_removed_by_default():
    short_term_memory = ShortTermMemory()
    msg = AIMessage(
        content="",
        tool_calls=[{"id": "call_1", "name": "tool_a", "args": {}}],
        additional_kwargs={"raw_tool_text": "debug", "keep": "value"},
    )
    appended = short_term_memory.append_assistant_tool_call(msg)
    assert "raw_tool_text" not in appended.additional_kwargs
    assert appended.additional_kwargs["keep"] == "value"


@pytest.mark.unit
def test_ut_run_026_short_term_memory_clear_empties_state():
    short_term_memory = ShortTermMemory()
    short_term_memory.append_tool_result(
        ToolMessage(content="done", tool_call_id="call_1", name="tool_a", status="success")
    )
    short_term_memory.clear()
    assert short_term_memory.messages() == []


@pytest.mark.unit
def test_ut_run_027_short_term_memory_emits_append_payload_with_token_estimates():
    events = []
    short_term_memory = ShortTermMemory(
        config=ShortTermMemoryConfig(on_message_appended=events.append, log_token_estimates=True)
    )
    short_term_memory.append_tool_result(
        ToolMessage(content="done", tool_call_id="call_1", name="tool_a", status="success")
    )
    assert events[0]["event"] == "short_term_memory_message_appended"
    assert events[0]["message_tokens_estimate"] is not None
