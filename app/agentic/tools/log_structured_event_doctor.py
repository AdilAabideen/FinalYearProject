from langchain.tools import tool
from pydantic import BaseModel, Field

from typing import Literal

class LogStructuredEventInput(BaseModel):
    event_type: Literal[
        "plan_created",
        "uptriage_applied",
        "uptriage_not_applied",
        "final_output_ready"
    ] = Field(
        ...,
        description="The type of milestone event being logged."
    )

    step: str = Field(
        ...,
        description="The workflow step this event relates to."
    )

    summary: str = Field(
        ...,
        description="Short one-sentence summary of the event."
    )

    tag: Literal["info", "important", "completed"] = Field(
        default="info",
        description="Lightweight event tag."
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

