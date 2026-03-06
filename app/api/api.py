from fastapi import APIRouter
from app.api.endpoints import medrecon

api_router = APIRouter()

api_router.include_router(medrecon.router, prefix="/medrecon", tags=["medrecon"])

