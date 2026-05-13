from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from app.agentic.HandRolledAgent import AgentKernel
from app.agentic.runtime.failure_taxonomy import FailureCategory
from app.agentic.runtime.runtime_config import RuntimeConfig


def _noop_tool() -> dict:
    """Return an empty payload."""
    return {}


class _PermissiveGenericModel:
    def __init__(self) -> None:
        self.bound_kwargs = None

    def bind_tools(self, tools, tool_choice="any", **kwargs):
        self.bound_kwargs = dict(kwargs)
        return self

    async def ainvoke(self, _messages):
        return AIMessage(content='{"value":"ok"}')


class _RuntimeHintAwareModel(_PermissiveGenericModel):
    def _llm_type(self) -> str:
        return "llama-server-chat"


@pytest.mark.unit
def test_ut_run_028_runtime_config_rejects_max_tool_calls_per_turn_below_one():
    with pytest.raises(ValueError):
        RuntimeConfig(max_tool_calls_per_turn=0)


@pytest.mark.unit
def test_ut_run_029_runtime_config_rejects_negative_malformed_retry_count():
    with pytest.raises(ValueError):
        RuntimeConfig(max_malformed_tool_retries_per_tool=-1)


@pytest.mark.unit
def test_ut_run_030_failure_taxonomy_values_remain_stable():
    assert FailureCategory.UNKNOWN_TOOL.value == "unknown_tool"
    assert FailureCategory.FINAL_OUTPUT_INVALID.value == "final_output_invalid"


@pytest.mark.unit
def test_ut_run_031_payload_to_human_content_extracts_plain_string_input():
    assert AgentKernel._payload_to_human_content("hello") == "hello"


@pytest.mark.unit
def test_ut_run_033_payload_to_human_content_extracts_latest_user_message_from_dict_messages():
    payload = {"messages": [{"role": "user", "content": "first"}, {"role": "user", "content": "latest"}]}
    assert AgentKernel._payload_to_human_content(payload) == "latest"


@pytest.mark.unit
def test_ut_run_034_limit_tool_calls_splits_kept_and_dropped_calls_correctly():
    agent = object.__new__(AgentKernel)
    agent.max_tool_calls = 2
    kept, dropped = AgentKernel._limit_tool_calls(
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
    assert AgentKernel._parsed_to_payload_json("x") == {"value": "x"}


@pytest.mark.unit
def test_ut_run_036_bind_model_tools_omits_runtime_hints_for_generic_models():
    model = _PermissiveGenericModel()
    AgentKernel(model=model, tools=[_noop_tool])
    assert model.bound_kwargs == {}


@pytest.mark.unit
def test_ut_run_037_bind_model_tools_includes_runtime_hints_for_supported_wrappers():
    model = _RuntimeHintAwareModel()
    agent = AgentKernel(
        model=model,
        tools=[_noop_tool],
        agent_node_name="demo_agent",
        handoff_tool_names=["handoff_to_other"],
        runtime_config=RuntimeConfig(multi_agent=True),
    )
    assert model.bound_kwargs == {
        "agent_name": agent.agent_node_name,
        "multi_agent": True,
        "handoff_names": ["handoff_to_other"],
    }
