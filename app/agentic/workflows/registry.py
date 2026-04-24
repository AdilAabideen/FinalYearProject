from __future__ import annotations

from typing import Dict, List

from app.agentic.workflows.definitions.esi_swarm_v1.spec import ESI_SWARM_V1_SPEC
from app.agentic.workflows.workflow_definition import WorkflowDefinition
from app.agentic.workflows.workflow_spec import WorkflowSpec


WORKFLOW_REGISTRY: Dict[str, WorkflowSpec] = {
    ESI_SWARM_V1_SPEC.workflow_id: ESI_SWARM_V1_SPEC,
}


def get_workflow_spec(workflow_id: str) -> WorkflowSpec:
    try:
        return WORKFLOW_REGISTRY[workflow_id]
    except KeyError as exc:
        raise ValueError("Unknown workflow_id '{workflow_id}'.".format(workflow_id=workflow_id)) from exc


def get_workflow_definition(workflow_id: str) -> WorkflowDefinition:
    return get_workflow_spec(workflow_id).workflow_definition


def list_workflow_specs() -> List[WorkflowSpec]:
    return sorted(
        WORKFLOW_REGISTRY.values(),
        key=lambda workflow: (workflow.name.lower(), workflow.version),
    )


def list_workflow_definitions() -> List[WorkflowDefinition]:
    return sorted(
        [workflow.workflow_definition for workflow in WORKFLOW_REGISTRY.values()],
        key=lambda workflow: (workflow.metadata.name.lower(), workflow.metadata.version),
    )
