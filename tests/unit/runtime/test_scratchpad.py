from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.agentic.runtime.scratchpad import Scratchpad, ScratchpadConfig


@pytest.mark.unit
def test_ut_run_019_append_assistant_tool_call_message_succeeds():
    scratchpad = Scratchpad()
    msg = AIMessage(content="", tool_calls=[{"id": "call_1", "name": "tool_a", "args": {}}])
    scratchpad.append_assistant_tool_call(msg)
    assert len(scratchpad.messages()) == 1


@pytest.mark.unit
def test_ut_run_020_append_assistant_tool_call_without_tool_calls_raises_error():
    scratchpad = Scratchpad()
    with pytest.raises(ValueError):
        scratchpad.append_assistant_tool_call(AIMessage(content="no tools"))


@pytest.mark.unit
def test_ut_run_021_append_tool_result_clones_message_safely():
    scratchpad = Scratchpad()
    msg = ToolMessage(content="done", tool_call_id="call_1", name="tool_a", status="success")
    cloned = scratchpad.append_tool_result(msg)
    assert cloned is not msg
    assert cloned.content == "done"


@pytest.mark.unit
def test_ut_run_022_final_assistant_is_excluded_when_config_disables_it():
    scratchpad = Scratchpad(config=ScratchpadConfig(include_final_assistant_output=False))
    assert scratchpad.append_final_assistant(AIMessage(content="final")) is None


@pytest.mark.unit
def test_ut_run_024_raw_provider_debug_keys_removed_by_default():
    scratchpad = Scratchpad()
    msg = AIMessage(
        content="",
        tool_calls=[{"id": "call_1", "name": "tool_a", "args": {}}],
        additional_kwargs={"raw_tool_text": "debug", "keep": "value"},
    )
    appended = scratchpad.append_assistant_tool_call(msg)
    assert "raw_tool_text" not in appended.additional_kwargs
    assert appended.additional_kwargs["keep"] == "value"


@pytest.mark.unit
def test_ut_run_026_scratchpad_clear_empties_state():
    scratchpad = Scratchpad()
    scratchpad.append_tool_result(ToolMessage(content="done", tool_call_id="call_1", name="tool_a", status="success"))
    scratchpad.clear()
    assert scratchpad.messages() == []


@pytest.mark.unit
def test_ut_run_027_scratchpad_emits_append_payload_with_token_estimates():
    events = []
    scratchpad = Scratchpad(
        config=ScratchpadConfig(on_message_appended=events.append, log_token_estimates=True)
    )
    scratchpad.append_tool_result(ToolMessage(content="done", tool_call_id="call_1", name="tool_a", status="success"))
    assert events[0]["event"] == "scratchpad_message_appended"
    assert events[0]["message_tokens_estimate"] is not None
