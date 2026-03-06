from __future__ import annotations
import json
import uuid

from app.agentic.llm import get_chat_model
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from app.agentic.prompts.vitals_agent_prompt import SYSTEM_PROMPT
from app.schemas.vitals_agent import VitalsAgentInput

from app.agentic.tools.vitals_agent.confounders import get_vitals_confounders
from app.agentic.tools.vitals_agent.compute_esi_danger_zone import compute_esi_danger_zone
from app.agentic.tools.vitals_agent.compute_shock_index import compute_shock_index
from app.agentic.tools.vitals_agent.ault_bp_temp_triggers import adult_bp_temp_triggers
from app.agentic.tools.log_thought import log_thought

from app.schemas.vitals_agent import VitalsAgentOutput

def build_vitals_agent():
    """
    Build Simple React Agent for Vital Signs Analysis
    """
    try:
        agent = create_react_agent(
            model=get_chat_model(),
            tools=[get_vitals_confounders, compute_esi_danger_zone, compute_shock_index, adult_bp_temp_triggers, log_thought],
            prompt=SYSTEM_PROMPT,
            output_type=VitalsAgentOutput,
        )
        return agent
    except Exception as e:
        raise Exception(f"Error building vitals agent: {e}")


def _maybe_pretty_json(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    try:
        obj = json.loads(stripped)
    except Exception:
        return stripped
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def run_vitals_agent(input: VitalsAgentInput, *, verbose: bool = True):
    """
    Run Vital Signs Analysis
    """
    
    try:
        agent = build_vitals_agent()
        payload = {"messages": [("user", input.model_dump_json())]}

        if not verbose:
            return agent.invoke(payload)

        run_id = uuid.uuid4().hex[:8]
        final_state = None

        def _log(line: str) -> None:
            print(f"{line}")

        def _log_block(title: str, block: str) -> None:
            _log(title)
            if block:
                for ln in block.splitlines():
                    _log(f"  {ln}")

        _log("START")

        # Mode: values Data: {'messages': [HumanMessage(content='{"temperature":97.3,"heartrate":70.0,"resprate":18.0,"o2sat":95.0,"sbp":145.0,"dbp":80.0,"pain":6.0,"subject_id":12482649,"intime":"2143-03-21T07:46:00","chiefcomplaint":"Head lac, s/p Fall","age_years":52.21801877}', additional_kwargs={}, response_metadata={}, id='7743a643-8436-45f8-b5f0-8cccbead29bc')]}

        for mode, data in agent.stream(payload, stream_mode=["updates", "values"]):
            if mode == "values":
                final_state = data
                continue

            if mode != "updates" or not isinstance(data, dict):
                continue

            for node_name, node_update in data.items():
                if not isinstance(node_update, dict):
                    continue
                messages = node_update.get("messages")
                if not isinstance(messages, list):
                    continue

                for msg in messages:
                    if isinstance(msg, AIMessage):
                        tool_calls = getattr(msg, "tool_calls", None) or []
                        for tc in tool_calls:
                            name = tc.get("name") if isinstance(tc, dict) else None
                            args = tc.get("args") if isinstance(tc, dict) else None
                            call_id = tc.get("id") if isinstance(tc, dict) else None
                            if name:
                                suffix = f" ({call_id})" if call_id else ""
                                _log_block(
                                    f"TOOL CALL -> {name}{suffix}",
                                    _maybe_pretty_json(json.dumps(args)),
                                )

                        content = (getattr(msg, "content", "") or "").strip()
                        if content:
                            _log_block(f"{node_name} ASSISTANT", _maybe_pretty_json(content))
                    elif isinstance(msg, ToolMessage):
                        tool_name = getattr(msg, "name", None) or "tool"
                        status = getattr(msg, "status", None) or "ok"
                        tool_call_id = getattr(msg, "tool_call_id", None)
                        content = (getattr(msg, "content", "") or "").strip()
                        suffix = f" ({tool_call_id})" if tool_call_id else ""
                        _log_block(
                            f"{node_name} TOOL RESULT <- {tool_name} ({status}){suffix}",
                            _maybe_pretty_json(content),
                        )

        _log("END")
        return final_state if final_state is not None else agent.invoke(payload)
    except Exception as e:
        raise Exception(f"Error running vitals agent: {e}")

    
