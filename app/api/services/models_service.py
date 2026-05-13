"""Models Service service helpers."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.agentic.model_registry import ModelSpec, get_registered_model_spec, list_registered_models


def list_registered_models_service() -> list[ModelSpec]:
    """List registered models service."""
    # Read the current list.
    return list_registered_models()


def get_registered_model_service(model_id: str) -> ModelSpec:
    """Return one registered model service."""
    # Read the current value.
    try:
        return get_registered_model_spec(model_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' was not found.",
        ) from exc
