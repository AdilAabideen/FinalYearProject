from __future__ import annotations

from app.agentic.workflows.definitions.esi_swarm_v1.agent_positions import AGENT_POSITIONS_MAP
from app.agentic.workflows.definitions.esi_swarm_v1.input_schema import SwarmV1Input
from app.agentic.workflows.definitions.esi_swarm_v1.workflow_definition import ESI_SWARM_V1
from app.agentic.workflows.workflow_spec import WorkflowInputSchemaSpec, WorkflowSpec


ESI_SWARM_V1_SPEC = WorkflowSpec(
    workflow_definition=ESI_SWARM_V1,
    input_schema=WorkflowInputSchemaSpec(
        schema_name="SwarmV1Input",
        model=SwarmV1Input,
        description="Frontend and API entry schema for the ESI Swarm V1 workflow.",
        metadata={
            "input_family": "triage_case",
            "rendering_hint": "form",
        },
    ),
    metadata={
        "definition_package": "app.agentic.workflows.definitions.esi_swarm_v1",
        "agent_positions": dict(AGENT_POSITIONS_MAP),
    },
)
