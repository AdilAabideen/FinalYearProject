from typing import Optional

from pydantic import BaseModel, Field
from langchain.tools import tool


class ShockIndexInput(BaseModel):
    hr: Optional[float] = Field(description="The Heart Rate of the Patient | CODE HR")
    sbp: Optional[float] = Field(description="The Systolic Blood Pressure of the Patient | CODE SBP")

@tool("compute_shock_index", args_schema=ShockIndexInput)
def compute_shock_index(
    hr: float,
    sbp: float
) -> dict:

    """
    Compute the Shock Index using the Heart Rate and Systolic Blood Pressure (HR, SBP) -> SI = HR / SBP
    Use this to tool to compute the Shock Index. You should use this Tool at the Start of the Execution of the Agent.
    ALWAYS USE THIS TOOL ATLEAST ONCE IN EXECUTION AND TAKE IN THE CONTEXT BEFORE MAKING THE FINAL DECISION.
    This Returns the Banding, If it is Hard ( Dangerous), Soft ( Caution) or Normal.

    If Band is Hard you should possible consider result Uptriage however look at Other vitals and context such as medications and chief complaint before making the final decision.
    If Band is Normal you can consider not Uptriaging
    If Band is Soft then there is a chance of Uptriage but look at Other Vitals heavily for other signs and then Uptriage

    Eg: 
    Input: HR = 100, SBP = 120
    Output: {"ok": True, "si": 0.833, "band": "soft"}

    Input: HR = 100, SBP = 80
    Output: {"ok": True, "si": 1.25, "band": "hard"}

    """

    si = hr / sbp

    # Conservative banding you can tune:
    # soft >=0.9, hard >=1.0
    if si >= 1.0:
        band = "hard -> Consider Uptriage However you should still look at Other Vitals and medications for contradictions before making a final contextual decision"
    elif si >= 0.9:
        band = "soft -> There is a chance of Uptriage but look at Other Vitals heavily for other signs and then Uptriage"
    else:
        band = "normal -> Consider Not Uptriaging per these Vitals however look at other vitals and context before making the final decision"


    return {"ok": True, "si": round(si, 3), "band": band}