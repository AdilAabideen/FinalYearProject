from datetime import datetime
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field

class VitalsAgentInput(BaseModel):
    temperature: float
    heartrate: float
    resprate: float
    o2sat: float
    sbp: float
    dbp: float
    pain: float
    subject_id: int
    intime: datetime
    chiefcomplaint: str
    age_years: float

class RecommendationOutput(BaseModel):
    consider_uptriage: bool = Field(description="Whether the agent recommends uptriage")
    reasoning_consider_uptriage: str = Field(description="The reasoning behind the recommendation to consider uptriage")
    confidence: Literal["low", "medium", "high"] = Field(description="The confidence in the recommendation of the agent")

class VitalsAgentOutput(BaseModel):
    ok: bool = Field(description="Whether the agent was able to complete the task successfully and did not encounter any errors")
    recommendation: RecommendationOutput = Field(description="The recommendation of the agent")
    