from __future__ import annotations

from datetime import datetime
from typing import Literal, List

from pydantic import BaseModel, Field


class ES1AgentInput(BaseModel):
    gender: str
    race: str
    arrival_transport: str
    pain: str
    chiefcomplaint: str
    age: float | int
    tiragecase: str



class ES1AgentOutput(BaseModel):
    is_esi1: bool = Field(
        ...,
        description="Whether the case is ESI-1 or NOT ESI-1"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence between 0 and 1."
    )
    case_summary: str = Field(
        ...,
        description="A brief summary of the case."
    )
    key_risks: List[str] = Field(
        default_factory=list,
        description="Important risks or high-risk features identified."
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Important information missing from the case."
    )
    justification: str = Field(
        ...,
        description="Brief rationale for the provisional ESI decision."
    )

