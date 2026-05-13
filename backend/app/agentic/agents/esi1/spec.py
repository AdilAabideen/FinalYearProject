"""Spec module helpers."""

from __future__ import annotations

import json
import os
import sys
import uuid
from typing import Optional

from langchain_core.messages import AIMessage, ToolMessage
from app.agentic.agents.base.spec import AgentSpec
from app.agentic.handoff import create_handoff_tools
from app.agentic.model_registry import get_chat_model, resolve_model_spec
from app.agentic.runtime import AgentRuntime, RuntimeConfig
from app.config import settings

from .prompt import HANDOFF_REQUIREMENTS, SINGLE_AGENT_OUTPUT_REQUIREMENTS, SYSTEM_PROMPT
from .tools import TOOLS
from .evaluator import ES1AcuityEvaluator
from .handoffs import HANDOFFS

from app.agentic.AgentRuntime import AgentKernel
from .schema import ES1AgentInput, ES1AgentOutput


def build_es1_agent(runtime: AgentRuntime, runtime_config: Optional[RuntimeConfig] = None):
    """Build the ES1 agent."""
    # Build the next value.
    try:
        handoff_tools = create_handoff_tools("esi1_agent", HANDOFFS)
        handoff_tool_names = [tool.name for tool in handoff_tools]
        tools = [*TOOLS, *handoff_tools] if runtime_config and runtime_config.multi_agent else TOOLS
        return AgentKernel(
            model=runtime.model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            single_agent_prompt_addon=SINGLE_AGENT_OUTPUT_REQUIREMENTS,
            multi_agent_prompt_addon=HANDOFF_REQUIREMENTS,
            response_format=ES1AgentOutput,
            agent_node_name="esi1_agent",
            handoff_tool_names=handoff_tool_names,
            runtime_config=runtime_config,
        )
    except Exception as e:
        raise Exception(f"Error building vitals agent: {e}")


ESI1_AGENT_SPEC = AgentSpec(
    name="esi1_agent",
    title="ESI1 Agent",
    description="Identifies ESI-1 cases based on immediate life-saving criteria.",
    input_model=ES1AgentInput,
    output_model=ES1AgentOutput,
    tools=TOOLS,
    build=build_es1_agent,
    evaluator=ES1AcuityEvaluator(),
)


def _maybe_pretty_json(text: str) -> str:
    """Handle pretty json."""
    # Keep the main step clear.
    stripped = text.strip()
    if not stripped:
        return ""
    try:
        obj = json.loads(stripped)
    except Exception:
        return stripped
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def run_esi1_agent(input: ES1AgentInput, *, verbose: bool = True):
    """Run the vitals LangGraph agent with optional verbose stream logging."""
    # Kick off the main step.
    try:
        model_id = settings.OPENAI_MODEL
        model_spec = resolve_model_spec(model_id)
        runtime = AgentRuntime(
            model_id=model_id,
            model_spec=model_spec,
            model=get_chat_model(model_id),
        )
        agent = build_es1_agent(runtime)
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
            """Handle the value."""
            # Keep the main step clear.
            if not use_color or not codes:
                return text
            return "".join(codes) + text + RESET

        def _status_color(status: str) -> str:
            """Handle color."""
            # Keep the main step clear.
            normalized = (status or "").strip().lower()
            if normalized in {"error", "failed", "failure"}:
                return RED
            if normalized in {"success", "ok"}:
                return GREEN
            return YELLOW

        prefix = _c(f"[vitals-agent:{run_id}] ", DIM, GRAY)

        def _log(line: str) -> None:
            """Handle the value."""
            # Keep the main step clear.
            print(f"{prefix}{line}", flush=True)

        def _log_block(header: str, body: str) -> None:
            """Handle block."""
            # Keep the main step clear.
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
