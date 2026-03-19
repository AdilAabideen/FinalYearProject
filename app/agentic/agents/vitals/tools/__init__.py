from app.agentic.tools.log_thought import log_thought
from app.agentic.tools.vitals_agent.ault_bp_temp_triggers import adult_bp_temp_triggers
from app.agentic.tools.vitals_agent.compute_esi_danger_zone import compute_esi_danger_zone
from app.agentic.tools.vitals_agent.compute_shock_index import compute_shock_index
from app.agentic.tools.vitals_agent.confounders import get_vitals_confounders

TOOLS = [
    get_vitals_confounders,
    compute_esi_danger_zone,
    compute_shock_index,
    adult_bp_temp_triggers,
    log_thought,
]

