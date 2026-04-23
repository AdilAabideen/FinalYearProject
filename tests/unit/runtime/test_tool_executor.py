from __future__ import annotations

import asyncio

import pytest
from langchain_core.tools import tool
from pydantic import BaseModel

from app.agentic.runtime.tool_executor import ToolExecutor


class SampleModel(BaseModel):
    value: int


@tool
def dict_tool(value: int) -> dict:
    """Return a dict payload."""
    return {"value": value}


@tool
def string_tool(value: int) -> str:
    """Return a string payload."""
    return f"v={value}"


@tool
def model_tool(value: int) -> SampleModel:
    """Return a Pydantic payload."""
    return SampleModel(value=value)


@tool
def failing_tool(value: int) -> str:
    """Raise an execution error."""
    raise RuntimeError(f"boom-{value}")


async def _slow_tool_impl(value: int) -> str:
    """Sleep briefly to exercise timeout behavior."""
    await asyncio.sleep(0.2)
    return str(value)


slow_tool = tool(_slow_tool_impl)


@pytest.mark.unit
def test_ut_run_010_successful_tool_invocation_returns_success_toolmessage():
    traces = []
    executor = ToolExecutor({"dict_tool": dict_tool}, estimate_tool_result_tokens=len, emit_trace=traces.append)
    result = asyncio.run(executor.execute_tool_call({"id": "call_1", "name": "dict_tool", "args": {"value": 1}}, iteration=1))
    assert result.status == "success"
    assert result.tool_call_id == "call_1"


@pytest.mark.unit
def test_ut_run_011_successful_dict_result_serializes_as_json_text():
    executor = ToolExecutor({"dict_tool": dict_tool}, estimate_tool_result_tokens=len)
    result = asyncio.run(executor.execute_tool_call({"id": "call_1", "name": "dict_tool", "args": {"value": 1}}, iteration=1))
    assert result.content == '{"value": 1}'


@pytest.mark.unit
def test_ut_run_012_successful_pydantic_result_serializes_correctly():
    executor = ToolExecutor({"model_tool": model_tool}, estimate_tool_result_tokens=len)
    result = asyncio.run(executor.execute_tool_call({"id": "call_1", "name": "model_tool", "args": {"value": 2}}, iteration=1))
    assert result.content == '{"value":2}'


@pytest.mark.unit
def test_ut_run_013_unknown_tool_returns_error_toolmessage():
    executor = ToolExecutor({}, estimate_tool_result_tokens=len)
    result = asyncio.run(executor.execute_tool_call({"id": "call_1", "name": "missing", "args": {}}, iteration=1))
    assert result.status == "error"
    assert "Unknown tool" in result.content


@pytest.mark.unit
def test_ut_run_014_tool_exception_is_captured_in_error_text():
    traces = []
    executor = ToolExecutor({"failing_tool": failing_tool}, estimate_tool_result_tokens=len, emit_trace=traces.append)
    result = asyncio.run(executor.execute_tool_call({"id": "call_1", "name": "failing_tool", "args": {"value": 3}}, iteration=1))
    assert result.status == "error"
    assert "boom-3" in result.content
    assert traces[0].error_text == "boom-3"


@pytest.mark.unit
def test_ut_run_015_metric_trace_emitted_on_success():
    traces = []
    executor = ToolExecutor({"string_tool": string_tool}, estimate_tool_result_tokens=len, emit_trace=traces.append)
    asyncio.run(executor.execute_tool_call({"id": "call_1", "name": "string_tool", "args": {"value": 4}}, iteration=1))
    assert traces[0].status == "success"


@pytest.mark.unit
def test_ut_run_016_metric_trace_emitted_on_failure():
    traces = []
    executor = ToolExecutor({"failing_tool": failing_tool}, estimate_tool_result_tokens=len, emit_trace=traces.append)
    asyncio.run(executor.execute_tool_call({"id": "call_1", "name": "failing_tool", "args": {"value": 5}}, iteration=1))
    assert traces[0].status == "error"
    assert traces[0].error_kind == "tool_execution_error"


@pytest.mark.unit
def test_ut_run_017_batched_tool_execution_preserves_yielded_index_mapping():
    executor = ToolExecutor({"dict_tool": dict_tool, "string_tool": string_tool}, estimate_tool_result_tokens=len)

    async def _collect():
        items = []
        async for idx, message in executor.execute_tool_calls_batched(
            [
                {"id": "call_1", "name": "dict_tool", "args": {"value": 1}},
                {"id": "call_2", "name": "string_tool", "args": {"value": 2}},
            ],
            iteration=1,
        ):
            items.append((idx, message))
        return items

    items = asyncio.run(_collect())
    assert {idx for idx, _ in items} == {0, 1}


@pytest.mark.unit
def test_ut_run_018_batched_execution_timeout_cancels_pending_tasks():
    executor = ToolExecutor({"_slow_tool_impl": slow_tool}, estimate_tool_result_tokens=len)

    async def _run():
        async for _ in executor.execute_tool_calls_batched(
            [{"id": "call_1", "name": "_slow_tool_impl", "args": {"value": 1}}],
            iteration=1,
            timeout_s=0.01,
        ):
            pass

    with pytest.raises(TimeoutError):
        asyncio.run(_run())
