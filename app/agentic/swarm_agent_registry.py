# swarm_agent_register.py
from __future__ import annotations
from typing import Callable, Dict, Optional

from app.agentic.HandRolledAgent import SSEHandrolledAgent
from app.agentic.agents.doctor.spec import build_doctor_agent
from app.agentic.agents.esi1.spec import build_es1_agent
from app.agentic.agents.esi2.spec import build_esi2_agent
from app.agentic.agents.esi345.spec import build_esi345_agent
from app.agentic.agents.vitals.spec import build_vitals_agent
from app.agentic.runtime import AgentRuntime, RuntimeConfig
from app.agentic.swarm_contract import AgentName


SwarmAgentBuilder = Callable[[AgentRuntime, Optional[RuntimeConfig]], SSEHandrolledAgent]


SWARM_AGENT_BUILDERS: Dict[AgentName, SwarmAgentBuilder] = {
    "esi1_agent": build_es1_agent,
    "esi2_agent": build_esi2_agent,
    "esi345_agent": build_esi345_agent,
    "vitals_agent": build_vitals_agent,
    "doctor_agent": build_doctor_agent,
}


def build_swarm_agent(
    agent_name: AgentName,
    runtime: AgentRuntime,
    runtime_config: Optional[RuntimeConfig] = None,
) -> SSEHandrolledAgent:
    """Build one real swarm agent by graph agent name."""
    try:
        builder = SWARM_AGENT_BUILDERS[agent_name]
    except KeyError as exc:
        raise ValueError("No swarm agent builder registered for '{agent}'.".format(agent=agent_name)) from exc
    return builder(runtime, runtime_config)


class SwarmAgentRegistry:
    """Per-run cache for real swarm agents."""

    def __init__(
        self,
        *,
        runtime: AgentRuntime,
        runtime_config: Optional[RuntimeConfig] = None,
    ) -> None:
        self.runtime = runtime
        self.runtime_config = runtime_config
        self._agents: Dict[AgentName, SSEHandrolledAgent] = {}

    def get(self, agent_name: AgentName) -> SSEHandrolledAgent:
        if agent_name not in self._agents:
            self._agents[agent_name] = build_swarm_agent(
                agent_name,
                self.runtime,
                self.runtime_config,
            )
        return self._agents[agent_name]

    def clear(self) -> None:
        self._agents.clear()
