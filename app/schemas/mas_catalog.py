from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class MASCatalogSummary(BaseModel):
    workflow_id: str = Field(description="Stable workflow identifier.")
    name: str = Field(description="UI-friendly workflow name.")
    version: str = Field(description="Workflow version string.")
    description: Optional[str] = Field(
        default=None,
        description="Short description for UI display.",
    )
    participating_agents_count: int = Field(
        description="Number of participating agent nodes in the workflow."
    )
    start_agents_count: int = Field(
        description="Number of agents that may start the workflow."
    )
    finalizing_agents_count: int = Field(
        description="Number of agents allowed to finalize the workflow."
    )
    gates_count: int = Field(description="Number of gate nodes in the workflow.")
    sources_count: int = Field(description="Number of logical sources in the workflow.")


class MASWorkflowMetadataRead(BaseModel):
    workflow_id: str = Field(description="Stable workflow identifier.")
    name: str = Field(description="UI-friendly workflow name.")
    version: str = Field(description="Workflow version string.")
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the workflow.",
    )


class MASSourceRead(BaseModel):
    source_id: str = Field(description="Stable identifier for a logical workflow source.")
    name: str = Field(description="Human-readable source name.")
    agent_names: list[str] = Field(
        default_factory=list,
        description="Agents whose handoffs satisfy this source.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional human-readable description of the source.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional rendering or workflow metadata for this source.",
    )


class MASGateRead(BaseModel):
    gate_id: str = Field(description="Stable node identifier for the gate.")
    name: str = Field(description="Human-readable gate name.")
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the gate's role in the workflow.",
    )
    required_sources: list[str] = Field(
        default_factory=list,
        description="Logical sources required before the gate may route forward.",
    )
    incoming_from: list[str] = Field(
        default_factory=list,
        description="Workflow nodes that may route into this gate.",
    )
    target_node: Optional[str] = Field(
        default=None,
        description="Primary node the gate routes to when ready.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow-specific gate metadata.",
    )


class MASCatalogDetail(BaseModel):
    metadata: MASWorkflowMetadataRead = Field(description="Workflow metadata.")
    participating_agents: list[str] = Field(
        default_factory=list,
        description="All agent nodes that participate in this workflow.",
    )
    start_agents: list[str] = Field(
        default_factory=list,
        description="Agent nodes that may start the workflow.",
    )
    finalizing_agents: list[str] = Field(
        default_factory=list,
        description="Agent nodes allowed to produce final output.",
    )
    allowed_handoffs: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Directed handoff edges keyed by source agent.",
    )
    sources: dict[str, MASSourceRead] = Field(
        default_factory=dict,
        description="Logical workflow sources or branches.",
    )
    gates: dict[str, MASGateRead] = Field(
        default_factory=dict,
        description="Gate nodes and their metadata.",
    )
    agent_metadata: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional rendering or classification metadata for agents.",
    )
    workflow_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional workflow-level metadata.",
    )
