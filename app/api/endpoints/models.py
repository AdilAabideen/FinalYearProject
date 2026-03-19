from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agentic.model_registry import ModelSpec, get_registered_model_spec, list_registered_models


router = APIRouter()


@router.get("", response_model=list[ModelSpec])
def list_models():
    return list_registered_models()


@router.get("/{model_id}", response_model=ModelSpec)
def get_model(model_id: str):
    try:
        return get_registered_model_spec(model_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Model not found")

