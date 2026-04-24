from fastapi import APIRouter
from app.api.endpoints import (
    agent_catalog,
    agent_tests,
    agent_runs,
    mas_catalog,
    models,
    medrecon,
    swarm_runs,
    vitals_agent,
)

api_router = APIRouter()

api_router.include_router(medrecon.router, prefix="/medrecon", tags=["medrecon"])
api_router.include_router(
    vitals_agent.router, prefix="/vitals-agent", tags=["vitals-agent"]
)
api_router.include_router(agent_runs.router, prefix="/agent-runs", tags=["agent-runs"])
api_router.include_router(swarm_runs.router, prefix="/swarm-runs", tags=["swarm-runs"])
api_router.include_router(agent_catalog.router, prefix="/agents", tags=["agents"])
api_router.include_router(mas_catalog.router, prefix="/mas", tags=["mas"])
api_router.include_router(agent_tests.router, prefix="/tests", tags=["tests"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
