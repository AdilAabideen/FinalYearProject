"""Api module helpers."""

from fastapi import APIRouter
from app.api.endpoints import (
    agent_catalog,
    agent_tests,
    mas_tests,
    agent_runs,
    mas_catalog,
    mas_execution,
    models,
    mas_runs,
)

api_router = APIRouter()

api_router.include_router(agent_runs.router, prefix="/agent-runs", tags=["agent-runs"])
api_router.include_router(mas_runs.router, prefix="/mas-runs", tags=["mas-runs"])
api_router.include_router(mas_runs.router, prefix="/swarm-runs", tags=["swarm-runs"])
api_router.include_router(agent_catalog.router, prefix="/agents", tags=["agents"])
api_router.include_router(mas_catalog.router, prefix="/mas", tags=["mas"])
api_router.include_router(mas_execution.router, prefix="/mas", tags=["mas"])
api_router.include_router(agent_tests.router, prefix="/tests", tags=["tests"])
api_router.include_router(mas_tests.router, prefix="/mas-tests", tags=["mas-tests"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
