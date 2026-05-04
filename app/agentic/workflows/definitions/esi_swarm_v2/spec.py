from __future__ import annotations

from app.agentic.workflows.definitions.esi_swarm_v2.evaluator import ESISwarmV2Evaluator
from app.agentic.workflows.definitions.esi_swarm_v2.agent_positions import AGENT_POSITIONS_MAP
from app.agentic.workflows.definitions.esi_swarm_v2.input_schema import SwarmV2Input
from app.agentic.workflows.definitions.esi_swarm_v2.workflow_definition import ESI_SWARM_V2
from app.agentic.workflows.workflow_spec import WorkflowInputSchemaSpec, WorkflowSpec


ESI_SWARM_V2_SPEC = WorkflowSpec(
    workflow_definition=ESI_SWARM_V2,
    input_schema=WorkflowInputSchemaSpec(
        schema_name="SwarmV2Input",
        model=SwarmV2Input,
        description="Frontend and API entry schema for the ESI Swarm V1 workflow.",
        metadata={
            "input_family": "triage_case",
            "rendering_hint": "form",
        },
    ),
    test_evaluator=ESISwarmV2Evaluator(),
    metadata={
        "definition_package": "app.agentic.workflows.definitions.esi_swarm_v2",
        "agent_positions": dict(AGENT_POSITIONS_MAP),
    },
)
