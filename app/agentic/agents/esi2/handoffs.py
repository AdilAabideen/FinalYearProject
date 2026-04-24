from pydantic import BaseModel, Field
from app.agentic.handoff import define_handoff
from typing import List


class ESI2ToESI345Payload(BaseModel):
    esi2_result: str = Field(
        ...,
        description="Outcome of the ESI-2 assessment. Usually 'not_esi2' when handing off to the ESI-3/4/5 agent."
    )
    brief_reason: str = Field(
        ...,
        description="Short explanation of why the case was not judged to require immediate life-saving intervention from the available information."
    )
    carry_forward_concerns: List[str] = Field(
        ...,
        description="Key concerns or unresolved issues that the ESI-3/4/5 agent should keep in mind during resource prediction."
    )
    focus_for_esi345: str = Field(
        ...,
        description="Short instruction describing what the ESI-3/4/5 agent should evaluate next, such as expected resource use and ESI-3/4/5 consistency."
    )

class ESI2ToDoctorPayload(BaseModel):
    decision: str = Field(
        ...,
        description="Result of the ESI-2 assessment, typically 'esi2'."
    )
    urgency: str = Field(
        ...,
        description="Short urgency label showing that immediate clinical attention is required, for example 'immediate' or 'critical'."
    )
    reason: str = Field(
        ...,
        description="Brief explanation of why the patient appears to meet ESI-2 criteria."
    )
    critical_concerns: List[str] = Field(
        ...,
        description="Key immediate threats or red flags identified from the case, such as airway compromise, severe respiratory distress, shock, or unresponsiveness."
    )
    request: str = Field(
        ...,
        description="Short escalation request telling the doctor agent what to do next."
    )

HANDOFFS = [
    define_handoff(
        source_agent="esi2_agent",
        target_agent="esi345_agent",
        payload_model=ESI2ToESI345Payload,
        description="Transfer to ESI-3/4/5 when ESI-2 criteria are not met.",
    ),
    define_handoff(
        source_agent="esi2_agent",
        target_agent="doctor_agent",
        payload_model=ESI2ToDoctorPayload,
        description="Transfer to Doctor when the Case is Confirmed to be ESI2.",
    )
]
