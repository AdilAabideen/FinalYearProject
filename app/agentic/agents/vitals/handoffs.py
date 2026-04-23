from pydantic import BaseModel, Field
from typing import List, Literal

from app.agentic.handoff import define_handoff


class VitalsToDoctorPayload(BaseModel):
    consider_uptriage: bool = Field(
        ...,
        description="Whether the vitals agent recommends that the case should be considered for up-triage."
    )
    urgency: Literal["low", "moderate", "high"] = Field(
        ...,
        description="How concerning the vitals pattern appears from a triage perspective."
    )
    reason: str = Field(
        ...,
        description="Brief explanation of why the vitals pattern is concerning."
    )
    abnormal_vitals: List[str] = Field(
        default_factory=list,
        description="Specific abnormal vital signs or physiological concerns identified."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        ...,
        description="Confidence of the vitals agent in the recommendation."
    )
    request: str = Field(
        ...,
        description="Short request telling the doctor agent what to review or decide next."
    )

HANDOFFS = [
    define_handoff(
        source_agent="vitals_agent",
        target_agent="doctor_agent",
        payload_model=VitalsToDoctorPayload,
        description="Transfer to the Doctor the Information About the Vitals",
    ),
]
