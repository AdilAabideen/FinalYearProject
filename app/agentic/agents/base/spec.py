from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.agentic.eval_types import AgentEvaluator
from app.agentic.runtime import AgentRuntime


@dataclass(frozen=True)
class AgentSpec:
    name: str
    title: str
    description: str
    input_model: Type[BaseModel]
    tools: Sequence[BaseTool]
    build: Callable[[AgentRuntime], Any]
    output_model: Optional[Type[BaseModel]] = None
    evaluator: Optional[AgentEvaluator] = None
