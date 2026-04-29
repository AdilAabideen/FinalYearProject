from langchain.tools import tool
from pydantic import BaseModel, Field

from typing import Literal

class LogResourceNeeded(BaseModel):
    resource_name: str = Field(
        ...,
        description="Name of the Resource Needed"
    )
    justification : str = Field(
        ...,
        description="Justification of the resource"
    )


@tool("log_resource", args_schema=LogResourceNeeded)
def log_resource(
    resource_name,
    justification
) -> dict:
    """
    Log Resource Prediction for ESI345
    """
    return {
        "resource_name" : resource_name,
        "justification" : justification
    }

