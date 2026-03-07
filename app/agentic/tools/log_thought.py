from langchain.tools import tool
from pydantic import BaseModel, Field

class LogThoughtInput(BaseModel):
    thought: str = Field(
        description="Short plan/justification. No diagnosis, no treatment. <= 25 words."
    )

@tool("log_thought", args_schema=LogThoughtInput)
def log_thought(thought: str) -> str:
    """Emit a short agent narration line for terminal observability."""
    return thought