"""Input Schema module helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, List, Union, Optional

from pydantic import AliasChoices, BaseModel, Field


class MASInput(BaseModel):
    gender: str = Field(description="Recorded patient gender at the time of triage.")
    race: str = Field(description="Recorded patient race or ethnicity category used in the source dataset.")
    arrival_transport: str = Field(
        validation_alias=AliasChoices("arrival_transport", "arrivaltransport", "arrival", "transfer"),
        description="How the patient arrived to the emergency department, such as walk-in or ambulance.",
    )
    pain: Optional[str] = Field(description="Reported pain level or pain assessment captured during intake.")
    chiefcomplaint: str = Field(
        validation_alias=AliasChoices("chiefcomplaint", "chief complaint", "chief_complaint"),
        description="Primary presenting complaint recorded at triage.",
    )
    age: Optional[float] = Field(description="Patient age at the time of the encounter.")
    tiragecase: str = Field(
        validation_alias=AliasChoices("tiragecase", "triage case", "triage_case"),
        description="Free-text triage case summary or scenario narrative.",
    )
    temperature: Optional[float] = Field(description="Measured body temperature during triage, typically in Celsius.")
    heartrate: Optional[float] = Field(description="Measured heart rate in beats per minute.")
    resprate: Optional[float] = Field(description="Measured respiratory rate in breaths per minute.")
    o2sat: Optional[float] = Field(description="Measured peripheral oxygen saturation percentage.")
    sbp: Optional[float] = Field(description="Measured systolic blood pressure.")
    dbp: Optional[float] = Field(description="Measured diastolic blood pressure.")

