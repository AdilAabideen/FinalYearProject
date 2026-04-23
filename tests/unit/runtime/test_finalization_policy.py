from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.agentic.runtime.finalization_policy import FinalizationPolicy
from app.agentic.runtime.runtime_config import RuntimeConfig


@pytest.mark.unit
def test_ut_run_001_strict_mode_requires_final_answer_tool():
    policy = FinalizationPolicy(
        config=RuntimeConfig(require_final_answer_tool=True, allow_plain_json_final_output=False)
    )
    decision = policy.maybe_finalize_from_assistant_no_tools(AIMessage(content='{"ok": true}'))
    assert decision.finalized is False
    assert decision.reason == "final_answer_tool_required"


@pytest.mark.unit
def test_ut_run_002_fallback_mode_accepts_plain_assistant_json():
    policy = FinalizationPolicy(config=RuntimeConfig(require_final_answer_tool=False))
    decision = policy.maybe_finalize_from_assistant_no_tools(AIMessage(content='{"recommendation": {"x": 1}}'))
    assert decision.finalized is True
    assert decision.output["ok"] is True


@pytest.mark.unit
def test_ut_run_003_plain_non_json_text_finalizes_only_when_allowed():
    policy = FinalizationPolicy(config=RuntimeConfig(require_final_answer_tool=False, allow_plain_json_final_output=True))
    decision = policy.maybe_finalize_from_assistant_no_tools(AIMessage(content="plain text"))
    assert decision.finalized is True
    assert decision.output == "plain text"


@pytest.mark.unit
def test_ut_run_004_valid_final_answer_tool_result_finalizes_successfully():
    policy = FinalizationPolicy(config=RuntimeConfig())
    decision = policy.maybe_finalize_from_tool_result(
        {"name": "final_answer"},
        ToolMessage(content='{"recommendation": {"a": 1}}', tool_call_id="call_1", name="final_answer", status="success"),
    )
    assert decision.finalized is True
    assert decision.output["ok"] is True


@pytest.mark.unit
def test_ut_run_005_non_final_answer_tool_does_not_finalize():
    policy = FinalizationPolicy(config=RuntimeConfig())
    decision = policy.maybe_finalize_from_tool_result(
        {"name": "other_tool"},
        ToolMessage(content='{"a": 1}', tool_call_id="call_1", name="other_tool", status="success"),
    )
    assert decision.finalized is False


@pytest.mark.unit
def test_ut_run_006_schema_validation_error_blocks_finalization():
    policy = FinalizationPolicy(
        config=RuntimeConfig(require_final_answer_tool=False),
        validate_output=lambda value: "bad schema" if value.get("bad") is True else None,
    )
    decision = policy.maybe_finalize_from_assistant_no_tools(AIMessage(content='{"bad": true}'))
    assert decision.finalized is False
    assert decision.reason == "schema_validation_error"


@pytest.mark.unit
def test_ut_run_007_no_output_fallback_produces_deterministic_payload():
    policy = FinalizationPolicy(config=RuntimeConfig())
    decision = policy.finalize_no_output()
    assert decision.output == {"ok": False, "error": "no_output"}


@pytest.mark.unit
def test_ut_run_008_invalid_output_fallback_contains_error_category_and_raw_output():
    policy = FinalizationPolicy(config=RuntimeConfig())
    decision = policy.finalize_invalid_output(reason="bad", raw_output="raw")
    assert decision.output["error"] == "final_output_invalid"
    assert decision.output["raw_output"] == "raw"


@pytest.mark.unit
def test_ut_run_009_output_normalization_sets_ok_true_when_recommendation_exists():
    policy = FinalizationPolicy(config=RuntimeConfig(require_final_answer_tool=False))
    decision = policy.maybe_finalize_from_assistant_no_tools(AIMessage(content='{"recommendation": {"consider_uptriage": true}}'))
    assert decision.output["ok"] is True
