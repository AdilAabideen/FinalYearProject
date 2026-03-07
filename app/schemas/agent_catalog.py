from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolCatalogItem(BaseModel):
    name: str = Field(description="Tool name as exposed to the agent/LLM.")
    description: str = Field(description="Human-readable tool description (from docstring).")
    args_schema: dict[str, Any] = Field(
        description="Pydantic JSON Schema describing the tool's input arguments."
    )


class AgentCatalogSummary(BaseModel):
    name: str = Field(description="Stable agent identifier (e.g. 'vitals_agent').")
    title: str = Field(description="UI-friendly agent name.")
    description: str = Field(description="Short description for UI display.")
    tools_count: int = Field(description="Number of tools available to this agent.")


class AgentCatalogDetail(BaseModel):
    name: str = Field(description="Stable agent identifier (e.g. 'vitals_agent').")
    title: str = Field(description="UI-friendly agent name.")
    description: str = Field(description="Short description for UI display.")
    input_schema: dict[str, Any] = Field(description="Pydantic JSON Schema for the agent input.")
    tools: list[ToolCatalogItem] = Field(description="Tools available to this agent.")

