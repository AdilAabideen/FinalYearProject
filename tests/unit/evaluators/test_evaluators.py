from __future__ import annotations

import pytest

from app.agentic.agents.esi1.evaluator import ES1AcuityEvaluator
from app.agentic.agents.esi2.evaluator import ESI2AcuityEvaluator
from app.agentic.agents.esi345.evaluator import ESI345AcuityEvaluator
from app.agentic.agents.vitals.evaluator import VitalsUptriageEvaluator


@pytest.mark.unit
def test_ut_evl_001_vitals_evaluator_validates_expected_contract_strictly():
    evaluator = VitalsUptriageEvaluator()
    with pytest.raises(ValueError):
        evaluator.validate_expected({"bad": True})


@pytest.mark.unit
def test_ut_evl_002_vitals_evaluator_returns_pass_for_matching_boolean():
    evaluator = VitalsUptriageEvaluator()
    result = evaluator.evaluate({"recommendation": {"consider_uptriage": True}}, {"recommendation": {"consider_uptriage": True}}, agent_status="succeeded")
    assert result.passed is True


@pytest.mark.unit
def test_ut_evl_004_vitals_evaluator_returns_fail_for_invalid_prediction_shape():
    evaluator = VitalsUptriageEvaluator()
    result = evaluator.evaluate({"recommendation": {"consider_uptriage": True}}, {"recommendation": {}}, agent_status="succeeded")
    assert result.metrics_json["invalid_pred"] is True


@pytest.mark.unit
def test_ut_evl_005_vitals_evaluator_aggregate_computes_confusion_counts_correctly():
    evaluator = VitalsUptriageEvaluator()
    results = [
        evaluator.evaluate({"recommendation": {"consider_uptriage": True}}, {"recommendation": {"consider_uptriage": True}}, agent_status="succeeded"),
        evaluator.evaluate({"recommendation": {"consider_uptriage": False}}, {"recommendation": {"consider_uptriage": False}}, agent_status="succeeded"),
    ]
    agg = evaluator.aggregate(results)
    assert agg["tp"] == 1
    assert agg["tn"] == 1


@pytest.mark.unit
def test_ut_evl_006_esi1_evaluator_treats_acuity_one_as_positive_class():
    evaluator = ES1AcuityEvaluator()
    result = evaluator.evaluate({"acuity": 1}, {"is_esi1": True}, agent_status="succeeded")
    assert result.passed is True


@pytest.mark.unit
def test_ut_evl_008_esi1_evaluator_fails_invalid_prediction():
    evaluator = ES1AcuityEvaluator()
    result = evaluator.evaluate({"acuity": 1}, {"is_esi1": "maybe"}, agent_status="succeeded")
    assert result.passed is False


@pytest.mark.unit
def test_ut_evl_009_esi2_evaluator_treats_acuity_two_as_positive_class():
    evaluator = ESI2AcuityEvaluator()
    result = evaluator.evaluate({"acuity": 2}, {"is_esi2": True}, agent_status="succeeded")
    assert result.passed is True


@pytest.mark.unit
def test_ut_evl_011_esi345_evaluator_returns_pass_for_acuity_and_resource_match():
    evaluator = ESI345AcuityEvaluator()
    result = evaluator.evaluate({"acuity": 3, "resources_used": 2}, {"esi_level": 3, "num_resources": 2}, agent_status="succeeded")
    assert result.passed is True
    assert result.score == 1.0


@pytest.mark.unit
def test_ut_evl_012_esi345_evaluator_returns_warning_for_resource_mismatch():
    evaluator = ESI345AcuityEvaluator()
    result = evaluator.evaluate({"acuity": 3, "resources_used": 2}, {"esi_level": 3, "num_resources": 1}, agent_status="succeeded")
    assert result.passed is True
    assert result.score == 0.5


@pytest.mark.unit
def test_ut_evl_014_esi345_evaluator_returns_fail_for_invalid_prediction():
    evaluator = ESI345AcuityEvaluator()
    result = evaluator.evaluate({"acuity": 3, "resources_used": 2}, {"esi_level": "x", "num_resources": 2}, agent_status="succeeded")
    assert result.metrics_json["invalid_pred"] is True


@pytest.mark.unit
def test_ut_evl_015_esi345_aggregate_computes_pass_warning_fail_counts_correctly():
    evaluator = ESI345AcuityEvaluator()
    results = [
        evaluator.evaluate({"acuity": 3, "resources_used": 2}, {"esi_level": 3, "num_resources": 2}, agent_status="succeeded"),
        evaluator.evaluate({"acuity": 3, "resources_used": 2}, {"esi_level": 3, "num_resources": 1}, agent_status="succeeded"),
        evaluator.evaluate({"acuity": 3, "resources_used": 2}, {"esi_level": 4, "num_resources": 2}, agent_status="succeeded"),
    ]
    agg = evaluator.aggregate(results)
    assert agg["pass_count"] == 1
    assert agg["warning_count"] == 1
    assert agg["fail_count"] == 1
