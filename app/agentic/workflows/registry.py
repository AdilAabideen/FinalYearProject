from __future__ import annotations

from typing import Dict, List

from app.agentic.workflows.definitions.esi_swarm_v1 import ESI_SWARM_V1
from app.agentic.workflows.workflow_definition import WorkflowDefinition


WORKFLOW_REGISTRY: Dict[str, WorkflowDefinition] = {
    ESI_SWARM_V1.metadata.workflow_id: ESI_SWARM_V1,
}


def get_workflow_definition(workflow_id: str) -> WorkflowDefinition:
    try:
        return WORKFLOW_REGISTRY[workflow_id]
    except KeyError as exc:
        raise ValueError("Unknown workflow_id '{workflow_id}'.".format(workflow_id=workflow_id)) from exc


def list_workflow_definitions() -> List[WorkflowDefinition]:
    return sorted(
        WORKFLOW_REGISTRY.values(),
        key=lambda workflow: (workflow.metadata.name.lower(), workflow.metadata.version),
    )
