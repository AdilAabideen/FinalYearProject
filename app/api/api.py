from fastapi import APIRouter
from app.api.endpoints import medrecon, vitals_agent

api_router = APIRouter()

api_router.include_router(medrecon.router, prefix="/medrecon", tags=["medrecon"])
api_router.include_router(
    vitals_agent.router, prefix="/vitals-agent", tags=["vitals-agent"]
)
