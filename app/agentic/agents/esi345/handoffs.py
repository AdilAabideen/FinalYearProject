from pydantic import BaseModel, Field
from app.agentic.handoff import define_handoff
from typing import List, Literal


class ESI345ToDoctorPayload(BaseModel):
    decision: str = Field(
        ...,
        description="Result of the ESI-345 assessment, usually indicating that the case needs doctor review or up-triage."
    )
    urgency: str = Field(
        ...,
        description="Short urgency label showing the level of concern, for example 'urgent', 'high', or 'reassess_now'."
    )
    reason: str = Field(
        ...,
        description="Brief explanation of why the case should be escalated from the ESI-345 stage to the doctor agent."
    )
    esi_level: Literal[3, 4, 5] = Field(
        ...,
        description="Which ESI level the case is currently judged to be in before doctor review."
    )
    num_resources: int = Field(
        ...,
        ge=0,
        description="The predicted number of ESI-counted resources required for the case."
    )
    predicted_resources: List[str] = Field(
        default_factory=list,
        description="Specific ESI resources likely needed, if any."
    )
    critical_concerns: List[str] = Field(
        default_factory=list,
        description="Key concerns, red flags, abnormal findings, or up-triage reasons the doctor agent should review."
    )
    request: str = Field(
        ...,
        description="Short escalation request telling the doctor agent what to review or decide next."
    )


HANDOFFS = [
    define_handoff(
        source_agent="esi345_agent",
        target_agent="doctor_agent",
        payload_model=ESI345ToDoctorPayload,
        description="Transfer to Doctor when the ESI-345 assessment identifies concerns requiring escalation or review.",
    ),
]