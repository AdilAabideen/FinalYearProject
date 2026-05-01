from typing import ClassVar, List, Literal

from pydantic import Field

from app.agentic.handoff import CoerciveHandoffPayload, define_handoff

class ESI2ToESI345Payload(CoerciveHandoffPayload):
    _bool_fields: ClassVar[frozenset[str]] = frozenset({"is_esi2"})
    _list_fields: ClassVar[frozenset[str]] = frozenset({"carry_forward_concerns"})

    is_esi2: Literal[False] = Field(
        ...,
        description="Confirmed ESI-2 decision."
    )
    reason: str = Field(
        ...,
        description="Short explanation of why the case was not judged to require immediate life-saving intervention from the available information."
    )
    carry_forward_concerns: List[str] = Field(
        default_factory=list,
        description="Key concerns or unresolved issues that the ESI-3/4/5 agent should keep in mind during resource prediction."
    )

class ESI2ToDoctorPayload(CoerciveHandoffPayload):
    _bool_fields: ClassVar[frozenset[str]] = frozenset({"is_esi2"})
    _list_fields: ClassVar[frozenset[str]] = frozenset({"critical_concerns"})

    is_esi2: Literal[True] = Field(
        ...,
        description="Confirmed ESI-2 decision."
    )
    reason: str = Field(
        ...,
        description="Brief explanation of why the patient appears to meet ESI-2 criteria."
    )
    critical_concerns: List[str] = Field(
        default_factory=list,
        description="Key immediate threats or red flags identified from the case, such as airway compromise, severe respiratory distress, shock, or unresponsiveness."
    )

HANDOFFS = [
    define_handoff(
        source_agent="esi2_agent",
        target_agent="esi345_agent",
        payload_model=ESI2ToESI345Payload,
        description="Transfer to ESI-3/4/5 when ESI-2 criteria are not met.",
        tool_name="final_esi2_false_handoff_to_esi345_agent"
    ),
    define_handoff(
        source_agent="esi2_agent",
        target_agent="doctor_agent",
        payload_model=ESI2ToDoctorPayload,
        description="Transfer to Doctor when the Case is Confirmed to be ESI2.",
        tool_name="final_esi2_true_handoff_to_doctor_agent"
    )
]
