from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from app.agentic.agents.agents import get_agent_spec, list_agent_specs
from app.schemas.agent_catalog import AgentCatalogDetail, AgentCatalogSummary, ToolCatalogItem


def _tool_args_schema(tool: Any) -> dict[str, Any]:
    args_schema = getattr(tool, "args_schema", None)
    if (
        args_schema is not None
        and isinstance(args_schema, type)
        and issubclass(args_schema, BaseModel)
    ):
        return args_schema.model_json_schema()

    args = getattr(tool, "args", None)
    if isinstance(args, dict):
        return {"title": getattr(tool, "name", "tool"), "type": "object", "properties": args}

    return {"title": getattr(tool, "name", "tool"), "type": "object", "properties": {}}


def list_agent_catalog() -> list[AgentCatalogSummary]:
    specs = sorted(list_agent_specs(), key=lambda s: s.name)
    return [
        AgentCatalogSummary(
            name=spec.name,
            title=spec.title,
            description=spec.description,
            tools_count=len(spec.tools),
        )
        for spec in specs
    ]


def get_agent_catalog(agent_name: str) -> AgentCatalogDetail:
    try:
        spec = get_agent_spec(agent_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown agent")

    tools = [
        ToolCatalogItem(
            name=getattr(tool, "name", "tool"),
            description=str(getattr(tool, "description", "") or ""),
            args_schema=_tool_args_schema(tool),
        )
        for tool in spec.tools
    ]

    return AgentCatalogDetail(
        name=spec.name,
        title=spec.title,
        description=spec.description,
        input_schema=spec.input_model.model_json_schema(),
        tools=tools,
    )
