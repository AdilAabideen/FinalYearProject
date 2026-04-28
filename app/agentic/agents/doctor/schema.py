from pydantic import BaseModel, Field, AliasChoices
from typing import List, Literal, Optional, Any, Union


class DoctorAgentInput(BaseModel):
    gender: str
    race: str
    arrival_transport: str = Field(
        validation_alias=AliasChoices("arrival_transport", "arrivaltransport", "arrival", "transfer")
    )
    pain: str
    chiefcomplaint: str = Field(
        validation_alias=AliasChoices("chiefcomplaint", "chief complaint", "chief_complaint")
    )
    age: Union[float, int]
    tiragecase: str = Field(
        validation_alias=AliasChoices("tiragecase", "triage case", "triage_case")
    )

    source_agent: Literal["esi1_agent", "esi2_agent", "esi345_agent"] = Field(
        ...,
        description="Which upstream triage pathway is sending the case to the doctor agent."
    )

    esi1_summary: Optional[str] = Field(
        default=None,
        description="Summary from the ESI-1 agent if the case came from the ESI-1 pathway."
    )
    esi1_reason: Optional[str] = Field(
        default=None,
        description="Reason from the ESI-1 agent if available."
    )
    esi1_critical_concerns: List[str] = Field(
        default_factory=list,
        description="Immediate threats identified by the ESI-1 agent."
    )

    esi2_summary: Optional[str] = Field(
        default=None,
        description="Summary from the ESI-2 agent if the case came from the ESI-2 pathway."
    )
    esi2_reason: Optional[str] = Field(
        default=None,
        description="Reason from the ESI-2 agent if available."
    )
    esi2_critical_concerns: List[str] = Field(
        default_factory=list,
        description="High-risk concerns identified by the ESI-2 agent."
    )

    esi_level_345: Optional[Literal[3, 4, 5]] = Field(
        default=None,
        description="Predicted ESI level from the ESI-345 agent."
    )
    num_resources: Optional[int] = Field(
        default=None,
        description="Predicted number of ESI-counted resources from the ESI-345 agent."
    )
    predicted_resources: List[str] = Field(
        default_factory=list,
        description="Predicted ESI-counted resources from the ESI-345 agent."
    )
    esi345_reason: Optional[str] = Field(
        default=None,
        description="Reasoning from the ESI-345 agent."
    )
    esi345_concerns: List[str] = Field(
        default_factory=list,
        description="Concerns or caveats raised by the ESI-345 agent."
    )

    vitals_consider_uptriage: Optional[bool] = Field(
        default=None,
        description="Whether the vitals agent recommends considering up-triage."
    )
    vitals_urgency: Optional[Literal["low", "moderate", "high"]] = Field(
        default=None,
        description="Urgency label from the vitals agent."
    )
    vitals_reason: Optional[str] = Field(
        default=None,
        description="Reasoning from the vitals agent."
    )
    abnormal_vitals: List[str] = Field(
        default_factory=list,
        description="Abnormal vital signs identified by the vitals agent."
    )
    vitals_confidence: Optional[Literal["low", "medium", "high"]] = Field(
        default=None,
        description="Confidence from the vitals agent."
    )



class DoctorAgentOutput(BaseModel):
    final_esi_level: Literal[1, 2, 3, 4, 5] = Field(
        ...,
        description="Final ESI level after doctor-agent review."
    )

    source_agent: Literal["esi1_agent", "esi2_agent", "esi345_agent"] = Field(
        ...,
        description="Upstream acuity agent that produced the main triage result."
    )

    accepted_upstream_result: bool = Field(
        ...,
        description="True if the upstream acuity result was accepted without changing the ESI level."
    )

    uptriaged: bool = Field(
        ...,
        description="True only if an ESI-345 result was changed to ESI-2 because of vitals."
    )

    decision_source: Literal[
        "esi1_accepted",
        "esi2_accepted",
        "esi345_accepted",
        "esi345_uptriaged_to_esi2"
    ] = Field(
        ...,
        description="Simple explanation of how the final decision was produced."
    )

    summary: str = Field(
        ...,
        description="Short clinician-facing final summary."
    )

    rationale: str = Field(
        ...,
        description="Concise explanation of why the final ESI level was kept or changed."
    )

    key_concerns: List[str] = Field(
        default_factory=list,
        description="Important concerns carried forward from upstream agents."
    )

    predicted_resources: List[str] = Field(
        default_factory=list,
        description="Predicted ESI-counted resources if the source was the ESI-345 agent."
    )

    abnormal_vitals_considered: List[str] = Field(
        default_factory=list,
        description="Abnormal vitals considered during doctor review."
    )

    next_actions: List[str] = Field(
        default_factory=list,
        description="Immediate workflow or clinical review actions."
    )