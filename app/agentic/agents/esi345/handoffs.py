from pydantic import BaseModel, Field
from app.agentic.handoff import define_handoff
from typing import List, Literal


class ESI345ToDoctorPayload(BaseModel):
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
    reason: str = Field(
        ...,
        description="Brief rationale for the provisional ESI decision."
    )


HANDOFFS = [
    define_handoff(
        source_agent="esi345_agent",
        target_agent="doctor_agent",
        payload_model=ESI345ToDoctorPayload,
        description="Transfer to Doctor when the ESI-345 assessment identifies concerns requiring escalation or review.",
        tool_name="final_esi345_result_handoff_to_doctor_agent"
    ),
]