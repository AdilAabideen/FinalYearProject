from fastapi import APIRouter
from app.api.endpoints import medicine

api_router = APIRouter()

api_router.include_router(medicine.router, prefix="/medicines", tags=["medicines"])

