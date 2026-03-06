from pydantic import BaseModel
from datetime import datetime

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