from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agentic.registry import get_agent_spec, list_agent_specs
from app.schemas.agent_catalog import (
    AgentCatalogDetail,
    AgentCatalogSummary,
    ToolCatalogItem,
)

router = APIRouter()


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


@router.get("", response_model=list[AgentCatalogSummary])
def list_agents():
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


@router.get("/{agent_name}", response_model=AgentCatalogDetail)
def get_agent(agent_name: str):
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

