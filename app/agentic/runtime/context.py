from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from app.agentic.model_registry import ModelSpec
from app.config import Settings


@dataclass(frozen=True)
class RuntimeContext:
    settings: Settings
    db: Session


@dataclass(frozen=True)
class AgentRuntime:
    model_id: str
    model_spec: ModelSpec
    model: BaseChatModel
