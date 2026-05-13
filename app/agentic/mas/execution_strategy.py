from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Mapping, Protocol, runtime_checkable

from app.agentic.mas_contract import AgentExecutionResult, AgentName
from app.agentic.workflows.workflow_definition import WorkflowDefinition


ExecutionStrategyMode = str


@dataclass(frozen=True)
class ExecutionRequest:
    """Reusable execution input for one workflow agent step.

    The graph builder and node executor should depend on this request shape
    rather than on workflow-specific demo helpers.
    """

    workflow: WorkflowDefinition
    agent_name: AgentName
    pending_agent_payload: Mapping[str, Any] = field(default_factory=dict)
    state_snapshot: Mapping[str, Any] = field(default_factory=dict)

    @property
    def workflow_id(self) -> str:
        return self.workflow.metadata.workflow_id

    @property
    def workflow_version(self) -> str:
        return self.workflow.metadata.version

    def payload_dict(self) -> Dict[str, Any]:
        return dict(self.pending_agent_payload)

    def state_dict(self) -> Dict[str, Any]:
        return dict(self.state_snapshot)


@runtime_checkable
class ExecutionStrategy(Protocol):
    """Contract for pluggable mas execution backends.

    Concrete strategies are responsible for executing one agent step under the
    current workflow and returning a normalized ``AgentExecutionResult``.
    """

    mode: ExecutionStrategyMode

    async def execute(self, request: ExecutionRequest) -> AgentExecutionResult:
        """Execute one workflow agent step and return the normalized result."""
        ...


ExecutionFn = Callable[[ExecutionRequest], Awaitable[AgentExecutionResult]]


@dataclass(frozen=True)
class CallableExecutionStrategy:
    """Simple async-backed strategy adapter."""

    mode: ExecutionStrategyMode
    execute_fn: ExecutionFn

    async def execute(self, request: ExecutionRequest) -> AgentExecutionResult:
        return await self.execute_fn(request)
