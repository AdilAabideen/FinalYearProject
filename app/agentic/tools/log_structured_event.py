from langchain.tools import tool
from pydantic import BaseModel, Field

from typing import Literal

class LogStructuredEventInput(BaseModel):
    event_type: Literal[
        "plan_created",
        "key_risk_detected",
        "missing_info_detected",
        "replan_required",
        "final_output_ready",
        "resource_needed",
    ] = Field(
        ...,
        description="The type of meaningful event being logged."
    )
    step: str = Field(
        ...,
        description="The workflow step this event relates to."
    )
    summary: str = Field(
        ...,
        description="A short one-sentence summary of what happened."
    )
    tag: Literal["info", "warning", "important", "completed"] = Field(
        default="info",
        description="A very lightweight general tag for the event."
    )


@tool("log_structured_event", args_schema=LogStructuredEventInput)
def log_structured_event(
    event_type: str,
    step: str,
    summary: str,
    tag: str = "info",
) -> dict:
    """
    Log a small structured event for lineage/debugging.
    Only use for meaningful transitions, not every thought.
    """
    return {
        "event_type": event_type,
        "step": step,
        "summary": summary,
        "tag": tag,
    }

