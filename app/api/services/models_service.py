from __future__ import annotations

from fastapi import HTTPException

from app.agentic.model_registry import ModelSpec, get_registered_model_spec, list_registered_models


def list_registered_models_service() -> list[ModelSpec]:
    return list_registered_models()


def get_registered_model_service(model_id: str) -> ModelSpec:
    try:
        return get_registered_model_spec(model_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Model not found")
