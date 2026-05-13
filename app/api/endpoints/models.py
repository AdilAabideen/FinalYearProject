"""Models API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.agentic.model_registry import ModelSpec
from app.api.services import models_service

router = APIRouter()


@router.get("", response_model=list[ModelSpec])
def list_models():
    """List models."""
    # Read the current list.
    return models_service.list_registered_models_service()
