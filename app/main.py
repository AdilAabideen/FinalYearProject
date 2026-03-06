from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.api.api import api_router

# Ensure models are imported so Base.metadata is populated before create_all.
import app.models  # noqa: F401

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Welcome to Emergency Severity Index Multi Agent V Monolithic Agent System"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
