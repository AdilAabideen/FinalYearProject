"""Agent Catalog API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.services import agent_catalog_service
from app.schemas.agent_catalog import AgentCatalogDetail, AgentCatalogSummary

router = APIRouter()


@router.get("", response_model=list[AgentCatalogSummary])
def list_agents():
    """List agents."""
    # Read the current list.
    return agent_catalog_service.list_agent_catalog()


@router.get("/{agent_name}", response_model=AgentCatalogDetail)
def get_agent(agent_name: str):
    """Return agent."""
    # Read the current value.
    return agent_catalog_service.get_agent_catalog(agent_name)
