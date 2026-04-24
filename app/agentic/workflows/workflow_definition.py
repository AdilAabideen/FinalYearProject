from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator


class WorkflowMetadata(BaseModel):
    workflow_id: str = Field(..., description="Stable identifier for the workflow definition.")
    name: str = Field(..., description="Human-readable workflow name.")
    version: str = Field(..., description="Workflow version string.")
    description: Optional[str] = Field(
        default=None,
        description="Optional human-readable description of the workflow.",
    )

    @model_validator(mode="after")
    def validate_metadata(self) -> "WorkflowMetadata":
        if not self.workflow_id.strip():
            raise ValueError("workflow_id must be non-empty.")
        if not self.name.strip():
            raise ValueError("name must be non-empty.")
        if not self.version.strip():
            raise ValueError("version must be non-empty.")
        return self


class GateNodeDefinition(BaseModel):
    gate_id: str = Field(..., description="Stable node identifier for the gate.")
    name: str = Field(..., description="Human-readable gate name.")
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the gate's role in the workflow.",
    )
    required_sources: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Logical source groups or upstream sources required before the gate may route forward.",
    )
    incoming_from: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Workflow nodes that may route into this gate.",
    )
    target_node: Optional[str] = Field(
        default=None,
        description="Primary node the gate routes to when ready.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow-specific gate metadata for rendering or later policy binding.",
    )

    @model_validator(mode="after")
    def validate_gate(self) -> "GateNodeDefinition":
        if not self.gate_id.strip():
            raise ValueError("gate_id must be non-empty.")
        if not self.name.strip():
            raise ValueError("gate name must be non-empty.")
        return self


class WorkflowDefinition(BaseModel):
    metadata: WorkflowMetadata = Field(..., description="Workflow metadata.")
    participating_agents: Tuple[str, ...] = Field(
        ...,
        description="All agent nodes that participate in this workflow.",
    )
    start_agents: Tuple[str, ...] = Field(
        ...,
        description="Agent nodes that may start the workflow.",
    )
    finalizing_agents: Tuple[str, ...] = Field(
        ...,
        description="Agent nodes allowed to produce final output.",
    )
    allowed_handoffs: Dict[str, Tuple[str, ...]] = Field(
        default_factory=dict,
        description="Directed handoff edges keyed by source agent.",
    )
    gates: Dict[str, GateNodeDefinition] = Field(
        default_factory=dict,
        description="Gate nodes and their metadata.",
    )
    agent_metadata: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional rendering or classification metadata for participating agents.",
    )
    workflow_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional workflow-level metadata for rendering or later kernel configuration.",
    )

    @model_validator(mode="after")
    def validate_definition(self) -> "WorkflowDefinition":
        participating_agents = list(self.participating_agents)
        if not participating_agents:
            raise ValueError("participating_agents must contain at least one agent.")
        if len(set(participating_agents)) != len(participating_agents):
            raise ValueError("participating_agents must be unique.")

        gate_ids = list(self.gates.keys())
        if len(set(gate_ids)) != len(gate_ids):
            raise ValueError("gate ids must be unique.")

        overlap = set(participating_agents).intersection(gate_ids)
        if overlap:
            raise ValueError(
                "agent names and gate ids must not overlap: {values}".format(
                    values=", ".join(sorted(overlap))
                )
            )

        for agent_name in self.start_agents:
            if agent_name not in participating_agents:
                raise ValueError(
                    "start agent '{agent}' is not declared in participating_agents.".format(agent=agent_name)
                )

        for agent_name in self.finalizing_agents:
            if agent_name not in participating_agents:
                raise ValueError(
                    "finalizing agent '{agent}' is not declared in participating_agents.".format(agent=agent_name)
                )

        for source_agent, target_agents in self.allowed_handoffs.items():
            if source_agent not in participating_agents:
                raise ValueError(
                    "allowed_handoffs source '{source}' is not a participating agent.".format(source=source_agent)
                )
            if len(set(target_agents)) != len(target_agents):
                raise ValueError(
                    "allowed_handoffs for source '{source}' must not contain duplicates.".format(
                        source=source_agent
                    )
                )
            for target_agent in target_agents:
                if target_agent not in participating_agents:
                    raise ValueError(
                        "allowed_handoffs target '{target}' from source '{source}' is not a participating agent.".format(
                            source=source_agent,
                            target=target_agent,
                        )
                    )

        all_nodes = set(participating_agents).union(gate_ids)
        for gate_id, gate in self.gates.items():
            if gate.gate_id != gate_id:
                raise ValueError(
                    "gate map key '{key}' must match gate_id '{gate_id}'.".format(
                        key=gate_id,
                        gate_id=gate.gate_id,
                    )
                )
            for source_node in gate.incoming_from:
                if source_node not in all_nodes:
                    raise ValueError(
                        "gate '{gate_id}' incoming_from node '{source}' is not a known workflow node.".format(
                            gate_id=gate_id,
                            source=source_node,
                        )
                    )
            if gate.target_node is not None and gate.target_node not in all_nodes:
                raise ValueError(
                    "gate '{gate_id}' target_node '{target}' is not a known workflow node.".format(
                        gate_id=gate_id,
                        target=gate.target_node,
                    )
                )

        return self

    @property
    def gate_ids(self) -> Tuple[str, ...]:
        return tuple(self.gates.keys())

    @property
    def all_nodes(self) -> Tuple[str, ...]:
        return tuple(list(self.participating_agents) + list(self.gate_ids))

    def allowed_targets_for(self, source_agent: str) -> Tuple[str, ...]:
        return tuple(self.allowed_handoffs.get(source_agent, ()))

    def is_start_agent(self, agent_name: str) -> bool:
        return agent_name in self.start_agents

    def is_finalizing_agent(self, agent_name: str) -> bool:
        return agent_name in self.finalizing_agents

    def is_gate_node(self, node_name: str) -> bool:
        return node_name in self.gates

    def graph_edges(self) -> List[Tuple[str, str]]:
        edges: List[Tuple[str, str]] = []
        for source_agent, target_agents in self.allowed_handoffs.items():
            for target_agent in target_agents:
                edges.append((source_agent, target_agent))
        for gate_id, gate in self.gates.items():
            for source_node in gate.incoming_from:
                edges.append((source_node, gate_id))
            if gate.target_node is not None:
                edges.append((gate_id, gate.target_node))
        return edges
