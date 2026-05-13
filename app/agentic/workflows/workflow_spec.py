"""Workflow Spec module helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

from app.agentic.mas_eval_types import WorkflowEvaluator
from app.agentic.workflows.workflow_definition import WorkflowDefinition


@dataclass(frozen=True)
class WorkflowInputSchemaSpec:
    """External entry contract for a workflow or MAS variant."""

    schema_name: str
    model: Type[BaseModel]
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def json_schema(self) -> Dict[str, Any]:
        """Handle schema."""
        # Keep the main step clear.
        return self.model.model_json_schema()


@dataclass(frozen=True)
class WorkflowSpec:
    """Unified registry entry for one workflow variant."""

    workflow_definition: WorkflowDefinition
    input_schema: WorkflowInputSchemaSpec
    test_evaluator: Optional[WorkflowEvaluator] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def workflow_id(self) -> str:
        """Handle id."""
        # Keep the main step clear.
        return self.workflow_definition.metadata.workflow_id

    @property
    def name(self) -> str:
        """Handle the value."""
        # Keep the main step clear.
        return self.workflow_definition.metadata.name

    @property
    def version(self) -> str:
        """Handle the value."""
        # Keep the main step clear.
        return self.workflow_definition.metadata.version
