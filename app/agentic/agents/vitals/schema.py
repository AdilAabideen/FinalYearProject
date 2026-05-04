from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class VitalsAgentInput(BaseModel):
    temperature: float
    heartrate: float
    resprate: float
    o2sat: float
    sbp: float
    dbp: float
    pain: float
    age_years: float
    chiefcomplaint: str


class VitalsAgentOutput(BaseModel):
    consider_uptriage: bool = Field(description="Whether the agent recommends uptriage")
    reasoning_consider_uptriage: str = Field(
        description="The reasoning behind the recommendation to consider uptriage"
    )
    abnormal_vitals : list[str] = Field(description="A list of Vitals that are abnormal")
    confidence: float = Field(
        description="The confidence in the recommendation of the agent"
    )
