"""Models Service service helpers."""

from __future__ import annotations

from app.agentic.model_registry import ModelSpec, list_registered_models


def list_registered_models_service() -> list[ModelSpec]:
    """List registered models service."""
    # Read the current list.
    return list_registered_models()
