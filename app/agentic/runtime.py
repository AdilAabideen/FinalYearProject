from __future__ import annotations
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import Settings
from app.agentic.model_registry import ModelSpec
from langchain_core.language_models.chat_models import BaseChatModel


@dataclass(frozen=True)
class RuntimeContext:
    settings: Settings
    db: Session


@dataclass(frozen=True)
class AgentRuntime:
    model_id: str
    model_spec: ModelSpec
    model: BaseChatModel
