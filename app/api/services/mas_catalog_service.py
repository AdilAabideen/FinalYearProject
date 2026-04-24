from __future__ import annotations

from fastapi import HTTPException

from app.agentic.workflows.registry import get_workflow_definition, list_workflow_definitions
from app.agentic.workflows.workflow_definition import (
    GateNodeDefinition,
    SourceDefinition,
    WorkflowDefinition,
)
from app.schemas.mas_catalog import (
    MASCatalogDetail,
    MASCatalogSummary,
    MASGateRead,
    MASSourceRead,
    MASWorkflowMetadataRead,
)


def _build_metadata(workflow: WorkflowDefinition) -> MASWorkflowMetadataRead:
    return MASWorkflowMetadataRead(
        workflow_id=workflow.metadata.workflow_id,
        name=workflow.metadata.name,
        version=workflow.metadata.version,
        description=workflow.metadata.description,
    )


def _build_source(source: SourceDefinition) -> MASSourceRead:
    return MASSourceRead(
        source_id=source.source_id,
        name=source.name,
        agent_names=list(source.agent_names),
        description=source.description,
        metadata=dict(source.metadata),
    )


def _build_gate(gate: GateNodeDefinition) -> MASGateRead:
    return MASGateRead(
        gate_id=gate.gate_id,
        name=gate.name,
        description=gate.description,
        required_sources=list(gate.required_sources),
        incoming_from=list(gate.incoming_from),
        target_node=gate.target_node,
        metadata=dict(gate.metadata),
    )


def list_mas_catalog() -> list[MASCatalogSummary]:
    workflows = list_workflow_definitions()
    return [
        MASCatalogSummary(
            workflow_id=workflow.metadata.workflow_id,
            name=workflow.metadata.name,
            version=workflow.metadata.version,
            description=workflow.metadata.description,
            participating_agents_count=len(workflow.participating_agents),
            start_agents_count=len(workflow.start_agents),
            finalizing_agents_count=len(workflow.finalizing_agents),
            gates_count=len(workflow.gates),
            sources_count=len(workflow.sources),
        )
        for workflow in workflows
    ]


def get_mas_catalog(workflow_id: str) -> MASCatalogDetail:
    try:
        workflow = get_workflow_definition(workflow_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Unknown workflow")

    return MASCatalogDetail(
        metadata=_build_metadata(workflow),
        participating_agents=list(workflow.participating_agents),
        start_agents=list(workflow.start_agents),
        finalizing_agents=list(workflow.finalizing_agents),
        allowed_handoffs={
            source_agent: list(target_agents)
            for source_agent, target_agents in workflow.allowed_handoffs.items()
        },
        sources={
            source_id: _build_source(source)
            for source_id, source in workflow.sources.items()
        },
        gates={
            gate_id: _build_gate(gate)
            for gate_id, gate in workflow.gates.items()
        },
        agent_metadata={
            agent_name: dict(metadata)
            for agent_name, metadata in workflow.agent_metadata.items()
        },
        workflow_metadata=dict(workflow.workflow_metadata),
    )
