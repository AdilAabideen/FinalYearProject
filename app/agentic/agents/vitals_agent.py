from __future__ import annotations
from app.agentic.llm import get_chat_model
from langgraph.prebuilt import create_react_agent
from app.agentic.prompts.vitals_agent_prompt import SYSTEM_PROMPT, USER_PROMPT
from app.schemas.vitals_agent import VitalsAgentInput

from app.agentic.tools.vitals_agent.confounders import get_vitals_confounders
from app.agentic.tools.vitals_agent.compute_esi_danger_zone import compute_esi_danger_zone
from app.agentic.tools.vitals_agent.compute_shock_index import compute_shock_index
from app.agentic.tools.vitals_agent.ault_bp_temp_triggers import adult_bp_temp_triggers


def build_vitals_agent():
    """
    Build Simple React Agent for Vital Signs Analysis
    """
    try:
        agent = create_react_agent(
            model=get_chat_model(),
            tools=[get_vitals_confounders, compute_esi_danger_zone, compute_shock_index, adult_bp_temp_triggers],
            prompt=SYSTEM_PROMPT,
        )
        return agent
    except Exception as e:
        raise Exception(f"Error building vitals agent: {e}")

def run_vitals_agent(input: VitalsAgentInput):
    """
    Run Vital Signs Analysis
    """
    
    try:
        agent = build_vitals_agent()
        return agent.invoke({"messages": [("user", input.model_dump_json())]},
            print_mode=["debug", "updates"]
        )
    except Exception as e:
        raise Exception(f"Error running vitals agent: {e}")

    
