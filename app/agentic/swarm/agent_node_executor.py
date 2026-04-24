from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional

from app.agentic.payload_builder import build_pending_agent_payload
from app.agentic.swarm.execution_strategy import ExecutionRequest, ExecutionStrategy
from app.agentic.swarm_contract import AgentExecutionResult, AgentName, HandoffEnvelope, SwarmState
from app.agentic.workflows.workflow_definition import WorkflowDefinition


PayloadBuilder = Callable[[AgentName, SwarmState], Dict[str, Any]]


@dataclass(frozen=True)
class AgentNodeExecutionOutcome:
    agent_name: AgentName
    pending_agent_payload: Dict[str, Any]
    result: AgentExecutionResult
    state_updates: Dict[str, Any]
    goto: Optional[str]
    terminal: bool = False


class AgentNodeExecutor:
    """Reusable runtime adapter for one workflow agent-node execution."""

    def __init__(
        self,
        *,
        workflow: WorkflowDefinition,
        strategy: ExecutionStrategy,
        payload_builder: PayloadBuilder = build_pending_agent_payload,
    ) -> None:
        self.workflow = workflow
        self.strategy = strategy
        self.payload_builder = payload_builder

    async def execute(self, *, agent_name: AgentName, state: SwarmState) -> AgentNodeExecutionOutcome:
        pending_agent_payload = self.payload_builder(agent_name, state)
        request = ExecutionRequest(
            workflow=self.workflow,
            agent_name=agent_name,
            pending_agent_payload=dict(pending_agent_payload),
            state_snapshot=dict(state),
        )
        result = await self.strategy.execute(request)
        updates = self._base_updates(
            agent_name=agent_name,
            pending_agent_payload=pending_agent_payload,
            result=result,
        )
        return self._finalize_outcome(
            agent_name=agent_name,
            pending_agent_payload=pending_agent_payload,
            result=result,
            updates=updates,
        )

    def _base_updates(
        self,
        *,
        agent_name: AgentName,
        pending_agent_payload: Dict[str, Any],
        result: AgentExecutionResult,
    ) -> Dict[str, Any]:
        return {
            "active_agent": agent_name,
            "pending_agent_payload": pending_agent_payload,
            "completed_agents": [agent_name],
            "execution_trace": [
                {
                    "event": "agent_executed",
                    "agent": agent_name,
                    "status": result.status,
                    "output": result.output,
                    "payload_metadata": pending_agent_payload.get("metadata", {}),
                }
            ],
        }

    def _finalize_outcome(
        self,
        *,
        agent_name: AgentName,
        pending_agent_payload: Dict[str, Any],
        result: AgentExecutionResult,
        updates: Dict[str, Any],
    ) -> AgentNodeExecutionOutcome:
        if result.status == "final":
            updates["final_output"] = result.final_output or {}
            updates["execution_trace"].append(
                {
                    "event": "final_output_created",
                    "agent": result.agent_name,
                    "final_output": result.final_output,
                }
            )
            return AgentNodeExecutionOutcome(
                agent_name=agent_name,
                pending_agent_payload=pending_agent_payload,
                result=result,
                state_updates=updates,
                goto=None,
                terminal=True,
            )

        if result.status == "error":
            updates["execution_trace"].append(
                {
                    "event": "agent_error",
                    "agent": result.agent_name,
                    "output": result.output,
                }
            )
            return AgentNodeExecutionOutcome(
                agent_name=agent_name,
                pending_agent_payload=pending_agent_payload,
                result=result,
                state_updates=updates,
                goto=None,
                terminal=True,
            )

        handoff = result.handoff
        if handoff is None:
            updates["execution_trace"].append(
                {
                    "event": "missing_handoff",
                    "agent": result.agent_name,
                }
            )
            return AgentNodeExecutionOutcome(
                agent_name=agent_name,
                pending_agent_payload=pending_agent_payload,
                result=result,
                state_updates=updates,
                goto=None,
                terminal=True,
            )

        handoff_dict = handoff.model_dump()
        updates["pending_handoff"] = handoff_dict
        updates["handoff_history"] = [handoff_dict]
        updates["execution_trace"].append(
            {
                "event": "handoff_created",
                "from_agent": handoff.from_agent,
                "target_agent": handoff.target_agent,
                "handoff_name": handoff.handoff_name,
            }
        )
        return AgentNodeExecutionOutcome(
            agent_name=agent_name,
            pending_agent_payload=pending_agent_payload,
            result=result,
            state_updates=updates,
            goto=self._route_handoff(handoff),
            terminal=False,
        )

    def _route_handoff(self, handoff: HandoffEnvelope) -> str:
        gate_id = self._matching_gate_for_handoff(handoff)
        if gate_id is not None:
            return gate_id
        return handoff.target_agent

    def _matching_gate_for_handoff(self, handoff: HandoffEnvelope) -> Optional[str]:
        matches = []
        source_ids = set(self.workflow.sources_for_agent(handoff.from_agent))
        for gate_id, gate in self.workflow.gates.items():
            if gate.target_node != handoff.target_agent:
                continue
            if gate.incoming_from and handoff.from_agent not in gate.incoming_from:
                continue
            if gate.required_sources and not source_ids.intersection(set(gate.required_sources)):
                continue
            matches.append(gate_id)

        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                "Multiple gates match handoff '{source}' -> '{target}': {gates}".format(
                    source=handoff.from_agent,
                    target=handoff.target_agent,
                    gates=", ".join(sorted(matches)),
                )
            )
        return matches[0]
