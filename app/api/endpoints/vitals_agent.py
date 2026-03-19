from fastapi import APIRouter

from app.api.services.vitals_agent_service import run_vitals_agent_service
from app.agentic.agents.vitals.schema import VitalsAgentInput

router = APIRouter()


@router.post("/run")
def vitals_agent_run(payload: VitalsAgentInput, verbose: bool = True):
    return run_vitals_agent_service(payload, verbose=verbose)
