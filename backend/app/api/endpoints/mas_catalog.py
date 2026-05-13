"""Mas Catalog API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.services import mas_catalog_service
from app.schemas.mas_catalog import MASCatalogDetail, MASCatalogSummary

router = APIRouter()


@router.get("", response_model=list[MASCatalogSummary])
def list_mas_workflows():
    """List mas workflows."""
    # Read the current list.
    return mas_catalog_service.list_mas_catalog()


@router.get("/{workflow_id}", response_model=MASCatalogDetail)
def get_mas_workflow(workflow_id: str):
    """Return mas workflow."""
    # Read the current value.
    return mas_catalog_service.get_mas_catalog(workflow_id)
