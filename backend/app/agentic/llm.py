"""Llm module helpers."""

from __future__ import annotations

from typing import Optional

from app.agentic.model_registry import get_chat_model as get_chat_model_by_id
from app.config import settings


def get_chat_model(model_id: Optional[str] = None):
    """
    Backwards-compatible helper for constructing the default chat model.

    New code should prefer `app.agentic.model_registry.get_chat_model(model_id)`.
    """
    # Read the current value.
    return get_chat_model_by_id(model_id or settings.OPENAI_MODEL)
