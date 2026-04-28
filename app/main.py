from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import SessionLocal, engine, Base, ensure_runtime_schema_upgrades
from app.api.api import api_router

# Create database tables
Base.metadata.create_all(bind=engine)
ensure_runtime_schema_upgrades()

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

@app.on_event("startup")
def _seed_test_data() -> None:
    from app.seed_agent_tests import (
        ensure_seed_single_agent_test_cases,
        ensure_seed_vitals_agent_test_cases,
    )
    from app.seed_mas_tests import ensure_seed_esi_swarm_v1_mas_test_cases

    db = SessionLocal()
    try:
        ensure_seed_vitals_agent_test_cases(db)
        ensure_seed_single_agent_test_cases(db)
        ensure_seed_esi_swarm_v1_mas_test_cases(db)
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Welcome to Emergency Severity Index Multi Agent V Monolithic Agent System"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
