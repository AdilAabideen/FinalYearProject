from __future__ import annotations

import json

from fastapi import HTTPException

from app.agentic.agents.vitals.schema import VitalsAgentInput


def run_vitals_agent_service(payload: VitalsAgentInput, *, verbose: bool = True):
    try:
        from app.agentic.agents.vitals.spec import run_vitals_agent

        result = run_vitals_agent(payload, verbose=verbose)
    except Exception as e:
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
