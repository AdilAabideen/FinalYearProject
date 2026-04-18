from __future__ import annotations

import json
import os
import sys
import uuid

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.agentic.agents.base.spec import AgentSpec
from app.agentic.model_registry import get_chat_model, resolve_model_spec
from app.agentic.runtime import AgentRuntime
from app.config import settings

from .prompt import SYSTEM_PROMPT
from .tools import TOOLS
from .evaluator import ESI345AcuityEvaluator

from app.agentic.HandRolledAgent import SSEHandrolledAgent
from .schema import ES345AgentInput, ES345AgentOutput

def build_esi345_agent(runtime: AgentRuntime):
    """Build the ESI345 agent."""
    try:
        return SSEHandrolledAgent(
            model=runtime.model,
            tools=TOOLS,
            system_prompt=SYSTEM_PROMPT,
            response_format=ES345AgentOutput,
        )
    except Exception as e:
        raise Exception(f"Error building ESI345 agent: {e}")


ESI345_AGENT_SPEC = AgentSpec(
    name="esi345_agent",
    title="ESI345 Agent",
    description="Identifies ESI-3, 4, or 5 cases based on immediate life-saving criteria.",
    input_model=ES345AgentInput,
    output_model=ES345AgentOutput,
    tools=TOOLS,
    build=build_esi345_agent,
    evaluator=ESI345AcuityEvaluator(),
)


def _maybe_pretty_json(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    try:
        obj = json.loads(stripped)
    except Exception:
        return stripped
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def run_esi345_agent(input: ES345AgentInput, *, verbose: bool = True):
    """Run the ESI345 agent with optional verbose stream logging."""
    try:
        model_id = settings.OPENAI_MODEL
        model_spec = resolve_model_spec(model_id)
        runtime = AgentRuntime(
            model_id=model_id,
            model_spec=model_spec,
            model=get_chat_model(model_id),
        )
        agent = build_esi345_agent(runtime)
        payload = {"messages": [("user", input.model_dump_json())]}

        if not verbose:
            return agent.invoke(payload)

        run_id = uuid.uuid4().hex[:8]
        final_state = None

        use_color = (
            (os.environ.get("FORCE_COLOR") == "1" or sys.stdout.isatty())
            and os.environ.get("NO_COLOR") is None
            and os.environ.get("TERM") != "dumb"
        )
        RESET = "\x1b[0m"
        BOLD = "\x1b[1m"
        DIM = "\x1b[2m"
        RED = "\x1b[31m"
        GREEN = "\x1b[32m"
        YELLOW = "\x1b[33m"
        MAGENTA = "\x1b[35m"
        CYAN = "\x1b[36m"
        GRAY = "\x1b[90m"

        def _c(text: str, *codes: str) -> str:
            if not use_color or not codes:
                return text
            return "".join(codes) + text + RESET

        def _status_color(status: str) -> str:
            normalized = (status or "").strip().lower()
            if normalized in {"error", "failed", "failure"}:
                return RED
            if normalized in {"success", "ok"}:
                return GREEN
            return YELLOW

        prefix = _c(f"[vitals-agent:{run_id}] ", DIM, GRAY)

        def _log(line: str) -> None:
            print(f"{prefix}{line}", flush=True)

        def _log_block(header: str, body: str) -> None:
            _log(header)
            if body:
                for ln in body.splitlines():
                    _log(_c("  ", DIM, GRAY) + ln)
            print("", flush=True)

        _log(_c("START", DIM, GRAY))

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
                        content = (getattr(msg, "content", "") or "").strip()
                        if content:
                            _log_block(
                                f"{_c('ASSISTANT', BOLD, MAGENTA)} {node_name}",
                                _maybe_pretty_json(content),
                            )
                    elif isinstance(msg, ToolMessage):
                        tool_name = getattr(msg, "name", None) or "tool"
                        tool_status = getattr(msg, "status", None) or "ok"
                        tool_call_id = getattr(msg, "tool_call_id", None)
                        content = (getattr(msg, "content", "") or "").strip()
                        suffix = f" ({tool_call_id})" if tool_call_id else ""

                        if tool_name == "log_thought":
                            _log_block(
                                _c("THOUGHT", DIM, GRAY) + _c(suffix, DIM, GRAY),
                                _c(content, DIM, GRAY),
                            )
                        else:
                            _log_block(
                                f"{_c('RESULT', BOLD, CYAN)} {_c(tool_name, BOLD)} {_c(f'({tool_status})', _status_color(tool_status))}{_c(suffix, DIM, GRAY)}",
                                _maybe_pretty_json(content),
                            )

        _log(_c("END", DIM, GRAY))
        return final_state if final_state is not None else agent.invoke(payload)
    except Exception as e:
        raise Exception(f"Error running vitals agent: {e}")
