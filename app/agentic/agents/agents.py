from __future__ import annotations

from app.agentic.agents.base.spec import AgentSpec
from app.agentic.agents.vitals.spec import VITALS_AGENT_SPEC
from app.agentic.agents.doctor.spec import DOCTOR_AGENT_SPEC
from app.agentic.agents.esi1.spec import ESI1_AGENT_SPEC
from app.agentic.agents.esi2.spec import ESI2_AGENT_SPEC
from app.agentic.agents.esi345.spec import ESI345_AGENT_SPEC
from app.agentic.agents.doctor.spec import DOCTOR_AGENT_SPEC


AGENTS: dict[str, AgentSpec] = {
    VITALS_AGENT_SPEC.name: VITALS_AGENT_SPEC,
    DOCTOR_AGENT_SPEC.name: DOCTOR_AGENT_SPEC,
    ESI1_AGENT_SPEC.name: ESI1_AGENT_SPEC,
    ESI2_AGENT_SPEC.name: ESI2_AGENT_SPEC,
    ESI345_AGENT_SPEC.name: ESI345_AGENT_SPEC,
    DOCTOR_AGENT_SPEC.name : DOCTOR_AGENT_SPEC
}


def list_agent_specs() -> list[AgentSpec]:
    return list(AGENTS.values())


def supported_agent_names() -> set[str]:
    return set(AGENTS.keys())


def get_agent_spec(agent_name: str) -> AgentSpec:
    return AGENTS[agent_name]
