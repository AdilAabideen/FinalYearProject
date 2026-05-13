from __future__ import annotations

from app.agentic.workflows.definitions.esi_mas.agent_positions import AGENT_POSITIONS_MAP
from app.agentic.workflows.definitions.esi_mas.evaluator import ESIMASEvaluator
from app.agentic.workflows.definitions.esi_mas.input_schema import MASInput
from app.agentic.workflows.definitions.esi_mas.workflow_definition import ESI_MAS
from app.agentic.workflows.workflow_spec import WorkflowInputSchemaSpec, WorkflowSpec


ESI_MAS_SPEC = WorkflowSpec(
    workflow_definition=ESI_MAS,
    input_schema=WorkflowInputSchemaSpec(
        schema_name="MASInput",
        model=MASInput,
        description="Frontend and API entry schema for the ESI MAS workflow.",
        metadata={
            "input_family": "triage_case",
            "rendering_hint": "form",
        },
    ),
    test_evaluator=ESIMASEvaluator(),
    metadata={
        "definition_package": "app.agentic.workflows.definitions.esi_mas",
        "agent_positions": dict(AGENT_POSITIONS_MAP),
    },
)
