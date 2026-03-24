from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import List

class CreatePlanInput(BaseModel):
    objective: str = Field(
        ...,
        description="The main task the agent is trying to complete."
    )
    steps: List[str] = Field(
        ...,
        description="A short ordered list of lightweight execution steps."
    )
    notes: str | None = Field(
        default=None,
        description="Optional brief note for the plan. Keep short."
    )


@tool("create_plan", args_schema=CreatePlanInput)
def create_plan(
    objective: str,
    steps: List[str],
    notes: str | None = None,
) -> dict:
    """
    Create a lightweight structured plan for the current case.
    """
    return {
        "objective": objective,
        "steps": steps,
        "notes": notes,
    }
