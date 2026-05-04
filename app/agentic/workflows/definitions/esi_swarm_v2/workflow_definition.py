from __future__ import annotations

from app.agentic.workflows.workflow_definition import (
    GateNodeDefinition,
    SourceDefinition,
    WorkflowDefinition,
    WorkflowMetadata,
)


ESI_SWARM_V2 = WorkflowDefinition(
    metadata=WorkflowMetadata(
        workflow_id="esi_swarm_v2",
        name="ESI Swarm V2",
        version="1.0.0",
        description=(
            "Constrained multi-agent ESI workflow with parallel ESI1 and vitals starts, "
            "acuity handoffs through ESI2/ESI345, and doctor finalization."
        ),
    ),
    participating_agents=(
        "esi1_agent",
        "esi2_agent",
        "esi345_agent",
        "vitals_agent",
    ),
    start_agents=(
        "esi1_agent",
        "vitals_agent",
    ),
    finalizing_agents=(
        "esi1_agent",
        "esi2_agent",
        "esi345_agent",
    ),
    allowed_handoffs={
        "esi1_agent": ("esi2_agent", "esi345_agent"),
        "esi2_agent": ("esi345_agent", "esi1_agent"),
        "esi345_agent": ("esi2_agent", "esi1_agent"),
        "vitals_agent": (),
    },
    agent_metadata={
        "esi1_agent": {
            "role": "acuity",
            "stage": "decision_point_a",
            "can_handoff": True,
            "can_finalize": True,
        },
        "esi2_agent": {
            "role": "acuity",
            "stage": "decision_point_b",
            "can_handoff": True,
            "can_finalize": True,
        },
        "esi345_agent": {
            "role": "acuity",
            "stage": "decision_point_c",
            "can_handoff": True,
            "can_finalize": True,
        },
        "vitals_agent": {
            "role": "vitals",
            "stage": "parallel_support",
            "can_handoff": False,
            "can_finalize": False,
        },
    },
    workflow_metadata={
        "workflow_family": "esi_swarm",
        "execution_model": "constrained_swarm",
        "parallel_start": True,
    },
)
