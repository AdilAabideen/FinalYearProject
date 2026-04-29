from pydantic import BaseModel, Field
from app.agentic.handoff import define_handoff
from typing import List, Literal


class ESI1ToESI2Payload(BaseModel):
    esi1_result: Literal["esi1", "not_esi1"] = Field(
        ...,
        description="Outcome of the ESI-1 assessment. Usually 'not_esi1' when handing off to the ESI-2 agent."
    )
    brief_reason: str = Field(
        ...,
        description="Short explanation of why the case was not judged to require immediate life-saving intervention from the available information."
    )
    carry_forward_concerns: List[str] = Field(
        ...,
        description="Key concerns or unresolved issues that the ESI-2 agent should keep in mind during high-risk assessment."
    )
    focus_for_esi2: str = Field(
        ...,
        description="Short instruction describing what the ESI-2 agent should evaluate next, such as high-risk features, likely deterioration, or ESI-2 consistency."
    )

class ESI1ToDoctorPayload(BaseModel):
    decision: Literal["esi1", "not_esi1"] = Field(
        ...,
        description="Result of the ESI-1 assessment, typically 'esi1'."
    )
    urgency: str = Field(
        ...,
        description="Short urgency label showing that immediate clinical attention is required, for example 'immediate' or 'critical'."
    )
    reason: str = Field(
        ...,
        description="Brief explanation of why the patient appears to meet ESI-1 criteria."
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
        source_agent="esi1_agent",
        target_agent="esi2_agent",
        payload_model=ESI1ToESI2Payload,
        description="Transfer to ESI-2 when ESI-1 criteria are not met.",
    ),
    define_handoff(
        source_agent="esi1_agent",
        target_agent="doctor_agent",
        payload_model=ESI1ToDoctorPayload,
        description="Transfer to Doctor when the Case is Confirmed to be ESI1.",
    )
]