from __future__ import annotations

from fastapi import APIRouter

from app.agentic.model_registry import ModelSpec
from app.api.services import models_service

router = APIRouter()


@router.get("", response_model=list[ModelSpec])
def list_models():
    return models_service.list_registered_models_service()


@router.get("/{model_id}", response_model=ModelSpec)
def get_model(model_id: str):
    return models_service.get_registered_model_service(model_id)
