import json

from fastapi import APIRouter, HTTPException

from app.schemas.vitals_agent import VitalsAgentInput

router = APIRouter()


@router.post("/run")
def vitals_agent_run(payload: VitalsAgentInput, verbose: bool = True):
    """
    Run the vitals agent and return the final assistant message.
    """
    try:
        from app.agentic.agents.vitals_agent import run_vitals_agent

        result = run_vitals_agent(payload, verbose=verbose)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

    if isinstance(result, dict) and result.get("messages"):
        last = result["messages"][-1]
        content = getattr(last, "content", None)
        if content is None and isinstance(last, dict):
            content = last.get("content")

        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"output": content}

    return {"output": result}
