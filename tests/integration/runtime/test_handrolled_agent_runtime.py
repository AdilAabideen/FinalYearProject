"""Test Handrolled Agent Runtime test coverage."""

from __future__ import annotations

import asyncio

import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from app.agentic.HandRolledAgent import AgentKernel
from app.agentic.runtime.runtime_config import RuntimeConfig
from tests.doubles.fake_emitters import Collector
from tests.doubles.fake_provider import FakeChatModel


class OutputSchema(BaseModel):
    recommendation: dict


def lookup_value(value: str) -> dict:
    """Return a lookup payload."""
    # Keep the main step clear.
    return {"recommendation": {"value": value}}


def final_answer(recommendation: dict) -> dict:
    """Return the final answer payload."""
    # Keep the main step clear.
    return {"recommendation": recommendation}


async def _collect_stream(agent: AgentKernel, payload):
    """Handle stream."""
    # Keep the main step clear.
    items = []
    async for mode, data in agent.astream(payload, stream_mode=("updates", "values")):
        items.append((mode, data))
    return items


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_001_one_step_tool_call_then_final_answer_tool_succeeds():
    """Handle it run 001 one step tool call then final answer tool succeeds."""
    # Keep the main step clear.
    model = FakeChatModel(
        [
            AIMessage(content="", tool_calls=[{"id": "call_1", "name": "lookup_value", "args": {"value": "abc"}}]),
            AIMessage(content="", tool_calls=[{"id": "call_2", "name": "final_answer", "args": {"recommendation": {"value": "abc"}}}]),
        ]
    )
    agent = AgentKernel(model=model, tools=[lookup_value, final_answer], response_format=OutputSchema)
    output = asyncio.run(agent.ainvoke("hello"))
    assert output == {"recommendation": {"value": "abc"}, "ok": True}


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_003_text_recovered_raw_json_tool_call_path_succeeds():
    """Handle it run 003 text recovered raw json tool call path succeeds."""
    # Keep the main step clear.
    model = FakeChatModel(
        [
            AIMessage(content='{"tool_calls":[{"id":"call_1","name":"lookup_value","arguments":{"value":"text"}}]}'),
            AIMessage(content='{"tool_calls":[{"id":"call_2","name":"final_answer","arguments":{"recommendation":{"value":"text"}}}]}'),
        ]
    )
    agent = AgentKernel(model=model, tools=[lookup_value, final_answer], response_format=OutputSchema)
    output = asyncio.run(agent.ainvoke("hello"))
    assert output["recommendation"]["value"] == "text"


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_004_text_recovered_fenced_json_tool_call_path_succeeds():
    """Handle it run 004 text recovered fenced json tool call path succeeds."""
    # Keep the main step clear.
    model = FakeChatModel(
        [
            AIMessage(content='```json\n{"tool_calls":[{"id":"call_1","name":"lookup_value","arguments":{"value":"fenced"}}]}\n```'),
            AIMessage(content='```json\n{"tool_calls":[{"id":"call_2","name":"final_answer","arguments":{"recommendation":{"value":"fenced"}}}]}\n```'),
        ]
    )
    agent = AgentKernel(model=model, tools=[lookup_value, final_answer], response_format=OutputSchema)
    output = asyncio.run(agent.ainvoke("hello"))
    assert output["recommendation"]["value"] == "fenced"


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_005_malformed_tool_call_triggers_retry_feedback_and_then_succeeds():
    """Handle it run 005 malformed tool call triggers retry feedback and then succeeds."""
    # Keep the main step clear.
    events = Collector()
    model = FakeChatModel(
        [
            AIMessage(content='{"tool_calls":[{"name":"lookup_value","arguments":'),
            AIMessage(content='{"tool_calls":[{"id":"call_1","name":"lookup_value","arguments":{"value":"retry"}}]}'),
            AIMessage(content='{"tool_calls":[{"id":"call_2","name":"final_answer","arguments":{"recommendation":{"value":"retry"}}}]}'),
        ]
    )
    agent = AgentKernel(
        model=model,
        tools=[lookup_value, final_answer],
        response_format=OutputSchema,
        event_handlers=[events],
    )
    output = asyncio.run(agent.ainvoke("hello"))
    assert output["recommendation"]["value"] == "retry"


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_005b_malformed_tool_call_retry_is_tracked_per_tool_name():
    """Handle it run 005b malformed tool call retry is tracked per tool name."""
    # Keep the main step clear.
    model = FakeChatModel(
        [
            AIMessage(content='{"tool_calls":[{"name":"lookup_value","arguments":'),
            AIMessage(content='{"tool_calls":[{"id":"call_1","name":"lookup_value","arguments":{"value":"per-tool"}}]}'),
            AIMessage(content='{"tool_calls":[{"name":"final_answer","arguments":'),
            AIMessage(content='{"tool_calls":[{"id":"call_2","name":"final_answer","arguments":{"recommendation":{"value":"per-tool"}}}]}'),
        ]
    )
    agent = AgentKernel(
        model=model,
        tools=[lookup_value, final_answer],
        response_format=OutputSchema,
    )
    output = asyncio.run(agent.ainvoke("hello"))

    assert output["recommendation"]["value"] == "per-tool"


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_005c_same_tool_only_gets_one_malformed_retry():
    """Handle it run 005c same tool only gets one malformed retry."""
    # Keep the main step clear.
    model = FakeChatModel(
        [
            AIMessage(content='{"tool_calls":[{"name":"lookup_value","arguments":'),
            AIMessage(content='{"tool_calls":[{"name":"lookup_value","arguments":'),
        ]
    )
    agent = AgentKernel(
        model=model,
        tools=[lookup_value, final_answer],
        response_format=OutputSchema,
    )
    output = asyncio.run(agent.ainvoke("hello"))
    assert output["error"] == "final_output_invalid"
    assert output["reason"] == "schema_validation_error"


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_006_no_tool_calls_and_plain_final_json_finalizes_when_policy_allows():
    """Handle it run 006 no tool calls and plain final json finalizes when policy allows."""
    # Keep the main step clear.
    model = FakeChatModel([AIMessage(content='{"recommendation":{"value":"plain"}}')])
    agent = AgentKernel(
        model=model,
        tools=[],
        runtime_config=RuntimeConfig(require_final_answer_tool=False, allow_plain_json_final_output=True),
    )
    output = asyncio.run(agent.ainvoke("hello"))
    assert output["recommendation"]["value"] == "plain"


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_007_no_tool_calls_in_strict_mode_yields_invalid_output_fallback():
    """Handle it run 007 no tool calls in strict mode yields invalid output fallback."""
    # Keep the main step clear.
    model = FakeChatModel([AIMessage(content='{"recommendation":{"value":"plain"}}')])
    agent = AgentKernel(
        model=model,
        tools=[],
        runtime_config=RuntimeConfig(require_final_answer_tool=True, allow_plain_json_final_output=False),
    )
    output = asyncio.run(agent.ainvoke("hello"))
    assert output["error"] == "final_output_invalid"


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_008_unknown_tool_call_produces_tool_error_and_no_crash():
    """Handle it run 008 unknown tool call produces tool error and no crash."""
    # Keep the main step clear.
    model = FakeChatModel(
        [
            AIMessage(content="", tool_calls=[{"id": "call_1", "name": "missing_tool", "args": {}}]),
            AIMessage(content='{"recommendation":{"value":"after-error"}}'),
        ]
    )
    agent = AgentKernel(
        model=model,
        tools=[],
        runtime_config=RuntimeConfig(require_final_answer_tool=False, allow_plain_json_final_output=True),
    )
    output = asyncio.run(agent.ainvoke("hello"))
    assert output["recommendation"]["value"] == "after-error"


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_009_tool_exception_produces_tool_error_and_no_crash():
    """Handle it run 009 tool exception produces tool error and no crash."""
    # Keep the main step clear.
    def broken_tool(value: str) -> dict:
        """Raise a tool execution error."""
        # Keep the main step clear.
        raise RuntimeError("tool exploded")

    model = FakeChatModel(
        [
            AIMessage(content="", tool_calls=[{"id": "call_1", "name": "broken_tool", "args": {"value": "x"}}]),
            AIMessage(content='{"recommendation":{"value":"after-error"}}'),
        ]
    )
    agent = AgentKernel(
        model=model,
        tools=[broken_tool],
        runtime_config=RuntimeConfig(require_final_answer_tool=False, allow_plain_json_final_output=True),
    )
    output = asyncio.run(agent.ainvoke("hello"))
    assert output["recommendation"]["value"] == "after-error"


@pytest.mark.integration
@pytest.mark.runtime
def test_it_run_010_values_stream_reflects_done_false_then_done_true():
    """Handle it run 010 values stream reflects done false then done true."""
    # Keep the main step clear.
    model = FakeChatModel([AIMessage(content='{"recommendation":{"value":"plain"}}')])
    agent = AgentKernel(
        model=model,
        tools=[],
        runtime_config=RuntimeConfig(require_final_answer_tool=False, allow_plain_json_final_output=True),
    )
    items = asyncio.run(_collect_stream(agent, "hello"))
    values = [data for mode, data in items if mode == "values"]
    assert values[0]["done"] is False
    assert values[-1]["done"] is True
