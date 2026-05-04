from __future__ import annotations

import pytest

from app.agentic.agents.esi1.handoffs import ESI1ToDoctorPayload, ESI1ToESI2Payload
from app.agentic.agents.esi2.handoffs import ESI2ToDoctorPayload, ESI2ToESI345Payload
from app.agentic.agents.esi345.handoffs import ESI345ToDoctorPayload
from app.agentic.agents.vitals.handoffs import VitalsToDoctorPayload


@pytest.mark.unit
def test_ut_handoff_001_coerces_string_bool_and_defaults_missing_list_for_esi1_false():
    payload = ESI1ToESI2Payload.model_validate(
        {
            "is_esi1": "false",
            "reason": "Immediate life-saving intervention is not clearly required now.",
        }
    )
    assert payload.is_esi1 is False
    assert payload.brief_reason == "Immediate life-saving intervention is not clearly required now."
    assert payload.carry_forward_concerns == []


@pytest.mark.unit
def test_ut_handoff_002_wraps_string_into_list_for_esi1_true():
    payload = ESI1ToDoctorPayload.model_validate(
        {
            "is_esi1": "true",
            "reason": "Immediate airway intervention is required.",
            "critical_concerns": "airway compromise",
        }
    )
    assert payload.is_esi1 is True
    assert payload.critical_concerns == ["airway compromise"]


@pytest.mark.unit
def test_ut_handoff_003_defaults_missing_lists_for_esi2_handoffs():
    to_esi345 = ESI2ToESI345Payload.model_validate(
        {
            "is_esi2": "false",
            "reason": "High-risk criteria are not met.",
        }
    )
    to_doctor = ESI2ToDoctorPayload.model_validate(
        {
            "is_esi2": "true",
            "reason": "The patient is high-risk.",
        }
    )
    assert to_esi345.is_esi2 is False
    assert to_esi345.carry_forward_concerns == []
    assert to_doctor.is_esi2 is True
    assert to_doctor.critical_concerns == []


@pytest.mark.unit
def test_ut_handoff_004_accepts_stale_esi2_alias_fields():
    to_esi345 = ESI2ToESI345Payload.model_validate(
        {
            "esi1_result": "not_esi2",
            "reason": "High-risk criteria are not met.",
        }
    )
    to_doctor = ESI2ToDoctorPayload.model_validate(
        {
            "decision": "esi2",
            "reason": "The patient is high-risk.",
            "critical_concerns": [],
        }
    )
    to_doctor_missing_flag = ESI2ToDoctorPayload.model_validate(
        {
            "reason": "The patient is high-risk.",
            "critical_concerns": [],
        }
    )
    assert to_esi345.is_esi2 is False
    assert to_doctor.is_esi2 is True
    assert to_doctor_missing_flag.is_esi2 is True


@pytest.mark.unit
def test_ut_handoff_005_wraps_vitals_string_into_list_and_coerces_bool():
    payload = VitalsToDoctorPayload.model_validate(
        {
            "consider_uptriage": "false",
            "reason": "No dangerous vital-sign patterns were identified.",
            "abnormal_vitals": "HR 146, SI 1.15",
            "confidence": 0.8,
        }
    )
    assert payload.consider_uptriage is False
    assert payload.abnormal_vitals == ["HR 146, SI 1.15"]


@pytest.mark.unit
def test_ut_handoff_006_accepts_esi345_justification_alias():
    payload = ESI345ToDoctorPayload.model_validate(
        {
            "esi_level": 4,
            "num_resources": 1,
            "justification": "One imaging resource is likely required.",
        }
    )
    assert payload.esi_level == 4
    assert payload.reason == "One imaging resource is likely required."
    assert payload.predicted_resources == []
