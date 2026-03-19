from __future__ import annotations

from app.agentic.agents.base.spec import AgentSpec
from app.agentic.agents.vitals.spec import VITALS_AGENT_SPEC


AGENTS: dict[str, AgentSpec] = {
    VITALS_AGENT_SPEC.name: VITALS_AGENT_SPEC,
}


def list_agent_specs() -> list[AgentSpec]:
    return list(AGENTS.values())


def supported_agent_names() -> set[str]:
    return set(AGENTS.keys())


def get_agent_spec(agent_name: str) -> AgentSpec:
    return AGENTS[agent_name]
