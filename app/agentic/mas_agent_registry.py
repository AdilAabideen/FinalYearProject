# mas_agent_register.py
from __future__ import annotations
from typing import Callable, Dict, Optional

from app.agentic.HandRolledAgent import AgentKernel
from app.agentic.agents.doctor.spec import build_doctor_agent
from app.agentic.agents.esi1.spec import build_es1_agent
from app.agentic.agents.esi2.spec import build_esi2_agent
from app.agentic.agents.esi345.spec import build_esi345_agent
from app.agentic.agents.vitals.spec import build_vitals_agent
from app.agentic.runtime import AgentRuntime, RuntimeConfig
from app.agentic.mas_contract import AgentName


MASAgentBuilder = Callable[[AgentRuntime, Optional[RuntimeConfig]], AgentKernel]


MAS_AGENT_BUILDERS: Dict[AgentName, MASAgentBuilder] = {
    "esi1_agent": build_es1_agent,
    "esi2_agent": build_esi2_agent,
    "esi345_agent": build_esi345_agent,
    "vitals_agent": build_vitals_agent,
    "doctor_agent": build_doctor_agent,
}


def build_mas_agent(
    agent_name: AgentName,
    runtime: AgentRuntime,
    runtime_config: Optional[RuntimeConfig] = None,
) -> AgentKernel:
    """Build one real mas agent by graph agent name."""
    try:
        builder = MAS_AGENT_BUILDERS[agent_name]
    except KeyError as exc:
        raise ValueError("No mas agent builder registered for '{agent}'.".format(agent=agent_name)) from exc
    return builder(runtime, runtime_config)


class MASAgentRegistry:
    """Per-run cache for real mas agents."""

    def __init__(
        self,
        *,
        runtime: AgentRuntime,
        runtime_config: Optional[RuntimeConfig] = None,
    ) -> None:
        self.runtime = runtime
        self.runtime_config = runtime_config
        self._agents: Dict[AgentName, AgentKernel] = {}

    def get(self, agent_name: AgentName) -> AgentKernel:
        if agent_name not in self._agents:
            self._agents[agent_name] = build_mas_agent(
                agent_name,
                self.runtime,
                self.runtime_config,
            )
        return self._agents[agent_name]

    def clear(self) -> None:
        self._agents.clear()
