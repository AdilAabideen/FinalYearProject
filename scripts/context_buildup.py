#!/usr/bin/env python3
"""Context Buildup script helpers."""

from __future__ import annotations

import argparse
from importlib import import_module
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

from app.agentic.agents.agents import get_agent_spec
from app.agentic.models.medgemma_medical_chat import MedGemmaMedicalChatModel
from app.agentic.models.vllm_chat import VLLMChat

def temp_tool_instruction(
        tools: Sequence[dict[str, Any]],
        tool_choice: Optional[str],
    ) -> str:
        """Handle tool instruction."""
        # Keep the main step clear.
        prompt_tools: list[dict[str, Any]] = []
        for tool in tools:
            fn = tool.get("function", {})
            if not isinstance(fn, dict):
                continue
            name = fn.get("name")
            if not isinstance(name, str) or not name:
                continue
            prompt_tools.append(
                {
                    "name": name,
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {}),
                }
            )

        parts = [
            "<tool_rules>"
            " - When tools are available, you MUST follow this tool-calling contract.",
            " - Return a SINGLE JSON object (no markdown, no extra text).",
            " - Tool-call format (exact):",
            ' - {"tool_calls":[{"id":"call_<unique_id>","name":"<tool_name>","arguments":{...}}]}',
            " - Do NOT output multiple JSON objects. If you need multiple tool calls, put them in the single tool_calls array.",
            " - When you are ready to finalize, call the final_answer tool with the full final payload.",
            " - Tool call ids must be unique per call.",
        ]

        if tool_choice == "any":
            parts.append("You must call at least one tool (tool call is required).")
        elif tool_choice and tool_choice not in {"auto", "none"}:
            parts.append(f'You must call the tool "{tool_choice}".')
        else:
            parts.append("If no tool is needed, respond with normal assistant text (not JSON).")
        
        parts.append(
            "</tool_rules> \n"
            "<available_tools>",
        )

        for tool in prompt_tools:
            name = str(tool.get("name", ""))
            desc = str(tool.get("description", ""))
            parameters = tool.get("parameters", {}) if isinstance(tool.get("parameters"), dict) else {}
            properties = parameters.get("properties", {})
            required = parameters.get("required", [])

            header = (
                "FINAL ANSWER TOOL -- CALL THIS WHEN YOU WANT TO OUTPUT THE FINAL ANSWER"
                if name == "final_answer"
                else "TOOL"
            )

            parts.append(
                "\n".join(
                    [
                        "",
                        f"[{header}]",
                        f"TOOL NAME: {name}",
                        f"TOOL DESCRIPTION: {desc}",
                        f"TOOL PARAMETERS (arguments schema): {json.dumps(properties, ensure_ascii=False)}",
                        f"TOOL REQUIRED PARAMETERS: {json.dumps(required, ensure_ascii=False)}",
                    ]
                )
            )

        parts.append("</available_tools>")
        return "\n".join(parts)


def _parse_args() -> argparse.Namespace:
    """Parse args."""
    # Keep the output consistent.
    parser = argparse.ArgumentParser(
        description=(
            "Build and inspect model context exactly like Dr7/Llama wrappers do, "
            "without running the full agent loop."
        )
    )
    parser.add_argument("--provider", choices=("dr7", "llama"), default="dr7")
    parser.add_argument("--model-id", default=None, help="Optional model id override.")
    parser.add_argument("--system", default="", help="System prompt text.")
    parser.add_argument(
        "--use-agent-system-prompt",
        action="store_true",
        help=(
            "When --agent-name is set and no --messages-json/--system is provided, "
            "load SYSTEM_PROMPT from app.agentic.agents.<agent>.prompt."
        ),
    )
    parser.add_argument("--user", default="", help="User input text.")
    parser.add_argument(
        "--messages-json",
        default="",
        help=(
            "Path to JSON array of messages with role/content. "
            "Supported roles: system, user, assistant, tool."
        ),
    )
    parser.add_argument(
        "--tools-json",
        default="",
        help=(
            "Path to JSON array of tool definitions. "
            "Each item can be an OpenAI tool dict or a convert_to_openai_tool-compatible dict."
        ),
    )
    parser.add_argument(
        "--agent-name",
        default="",
        help="Optional agent name. Loads tools from app agent spec and merges with --tools-json.",
    )
    parser.add_argument("--tool-choice", default="any", help="Tool choice used by wrapper logic.")
    parser.add_argument(
        "--print-generate-messages-only",
        action="store_true",
        help=(
            "Print only the final normalized message list from simulated _generate "
            "(equivalent to print(json.dumps(dr7_messages/llama_messages)))."
        ),
    )
    parser.add_argument("--output", default="", help="Optional output JSON file path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    return parser.parse_args()


def _load_json_file(path: str) -> Any:
    """Load json file."""
    # Read the current value.
    payload = Path(path).read_text(encoding="utf-8")
    return json.loads(payload)


def _resolve_agent_system_prompt(agent_name: str) -> str:
    """Resolve agent system prompt."""
    # Pick the needed value.
    normalized = str(agent_name or "").strip()
    if not normalized:
        return ""

    module_key = normalized
    if module_key.endswith("_agent"):
        module_key = module_key[: -len("_agent")]

    module_path = f"app.agentic.agents.{module_key}.prompt"
    try:
        module = import_module(module_path)
    except Exception as exc:
        raise ValueError(
            f"Could not import prompt module for agent '{agent_name}' ({module_path})."
        ) from exc

    prompt = getattr(module, "SYSTEM_PROMPT", "")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(
            f"Prompt module '{module_path}' does not define a non-empty SYSTEM_PROMPT."
        )
    return prompt


def _to_base_message(item: dict[str, Any]) -> BaseMessage:
    """Handle base message."""
    # Keep the main step clear.
    role = str(item.get("role") or "").strip().lower()
    content = item.get("content", "")
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False, default=str)

    if role == "system":
        return SystemMessage(content=content)
    if role == "user":
        return HumanMessage(content=content)
    if role == "assistant":
        tool_calls = item.get("tool_calls")
        if not isinstance(tool_calls, list):
            tool_calls = []
        return AIMessage(content=content, tool_calls=tool_calls)
    if role == "tool":
        return ToolMessage(
            content=content,
            tool_call_id=str(item.get("tool_call_id") or "unknown"),
            name=(str(item.get("name")) if item.get("name") is not None else None),
            status=(str(item.get("status")) if item.get("status") is not None else "success"),
        )
    raise ValueError(f"Unsupported message role: {role!r}")


def _load_messages(messages_json: str, system_text: str, user_text: str) -> list[BaseMessage]:
    """Load messages."""
    # Read the current value.
    if messages_json:
        raw = _load_json_file(messages_json)
        if not isinstance(raw, list):
            raise ValueError("--messages-json must contain a JSON array.")
        out: list[BaseMessage] = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValueError(f"--messages-json item at index {idx} must be an object.")
            out.append(_to_base_message(item))
        return out

    out: list[BaseMessage] = []
    if system_text.strip():
        out.append(SystemMessage(content=system_text.strip()))
    if user_text.strip():
        out.append(HumanMessage(content=user_text.strip()))
    return out


def _load_tools(agent_name: str, tools_json: str) -> list[dict[str, Any]]:
    """Load tools."""
    # Read the current value.
    raw_tools: list[Any] = []
    spec = None
    if agent_name:
        spec = get_agent_spec(agent_name)
        raw_tools.extend(list(spec.tools or []))
        if getattr(spec, "output_model", None) is not None:
            existing_names: set[str] = set()
            for item in raw_tools:
                name = getattr(item, "name", None)
                if isinstance(name, str) and name.strip():
                    existing_names.add(name.strip())
            if "final_answer" not in existing_names:
                output_model = spec.output_model
                parameters: dict[str, Any] = {"type": "object", "additionalProperties": True}
                if output_model is not None and hasattr(output_model, "model_json_schema"):
                    try:
                        schema = output_model.model_json_schema()
                        if isinstance(schema, dict):
                            parameters = schema
                    except Exception:
                        pass
                raw_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": "final_answer",
                            "description": "Signal completion and return the final structured payload.",
                            "parameters": parameters,
                        },
                    }
                )
    if tools_json:
        parsed = _load_json_file(tools_json)
        if not isinstance(parsed, list):
            raise ValueError("--tools-json must contain a JSON array.")
        raw_tools.extend(parsed)

    converted: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for tool in raw_tools:
        converted_tool = convert_to_openai_tool(tool)
        if not isinstance(converted_tool, dict):
            continue
        fn = converted_tool.get("function")
        name = fn.get("name") if isinstance(fn, dict) else None
        if isinstance(name, str) and name:
            if name in seen_names:
                continue
            seen_names.add(name)
        converted.append(converted_tool)
    return converted


def _build_dr7_context(
    *,
    model_id: str,
    messages: Sequence[BaseMessage],
    tools: list[dict[str, Any]],
    tool_choice: Optional[str],
) -> dict[str, Any]:
    """Build dr7 context."""
    # Build the next value.
    model = MedGemmaMedicalChatModel(
        model=model_id,
        base_url="http://localhost/v1",
        api_key="debug",
    )

    kwargs: dict[str, Any] = {
        "tools": tools,
        "tool_choice": tool_choice,
    }
    bound_tools = kwargs.get("tools")
    _tool_choice = kwargs.get("tool_choice")
    filtered_tools: list[dict[str, Any]] = []
    if isinstance(bound_tools, list):
        filtered_tools = [t for t in bound_tools if isinstance(t, dict)]

    dr7_messages = model._to_dr7_messages(messages, allow_tool_messages=bool(filtered_tools))
    tool_instruction = None
    if filtered_tools:
        tool_instruction = temp_tool_instruction(filtered_tools, _tool_choice)
        if dr7_messages and dr7_messages[0].get("role") == "system":
            existing = (dr7_messages[0].get("content") or "").strip()
            if existing:
                dr7_messages[0]["content"] = f"{existing}\n\n{tool_instruction}"
            else:
                dr7_messages[0]["content"] = tool_instruction
        else:
            dr7_messages = [
                {"role": "system", "content": tool_instruction},
                *dr7_messages,
            ]
    normalized = model._normalize_dr7_messages(dr7_messages)
    return {
        "provider": "dr7",
        "model_id": model_id,
        "tool_choice": _tool_choice,
        "tool_instruction": tool_instruction,
        "raw_provider_messages": dr7_messages,
        "normalized_messages": normalized,
    }


def _build_llama_context(
    *,
    model_id: str,
    messages: Sequence[BaseMessage],
    tools: list[dict[str, Any]],
    tool_choice: Optional[str],
) -> dict[str, Any]:
    """Build llama context."""
    # Build the next value.
    model = VLLMChat(
        model=model_id,
        base_url="https://l99jmubodzvsex-8000.proxy.runpod.net/v1",
        api_key="",
    )

    kwargs: dict[str, Any] = {
        "tools": tools,
        "tool_choice": tool_choice,
    }
    bound_tools = kwargs.get("tools")
    _tool_choice = kwargs.get("tool_choice")
    filtered_tools: list[dict[str, Any]] = []
    if isinstance(bound_tools, list):
        filtered_tools = [t for t in bound_tools if isinstance(t, dict)]

    llama_messages = model._to_llama_messages(messages, allow_tool_messages=bool(filtered_tools))
    tool_instruction = None
    if filtered_tools:
        tool_instruction = temp_tool_instruction(filtered_tools, _tool_choice)
        if llama_messages and llama_messages[0].get("role") == "system":
            existing = (llama_messages[0].get("content") or "").strip()
            if existing:
                llama_messages[0]["content"] = f"{existing}\n\n{tool_instruction}"
            else:
                llama_messages[0]["content"] = tool_instruction
        else:
            llama_messages = [
                {"role": "system", "content": tool_instruction},
                *llama_messages,
            ]
    normalized = model._normalize_llama_messages(llama_messages)
    return {
        "provider": "llama",
        "model_id": model_id,
        "tool_choice": _tool_choice,
        "tool_instruction": tool_instruction,
        "raw_provider_messages": llama_messages,
        "normalized_messages": normalized,
    }


def main() -> int:
    """Handle the value."""
    # Keep the main step clear.
    args = _parse_args()
    system_text = args.system
    if (
        not args.messages_json
        and not system_text.strip()
        and args.use_agent_system_prompt
        and args.agent_name
    ):
        system_text = _resolve_agent_system_prompt(args.agent_name)

    messages = _load_messages(args.messages_json, system_text, args.user)
    tools = _load_tools(args.agent_name, args.tools_json)

    if args.provider == "dr7":
        model_id = args.model_id or "medgemma-4b-it"
        result = _build_dr7_context(
            model_id=model_id,
            messages=messages,
            tools=tools,
            tool_choice=args.tool_choice,
        )
    else:
        model_id = args.model_id or "esi1"
        result = _build_llama_context(
            model_id=model_id,
            messages=messages,
            tools=tools,
            tool_choice=args.tool_choice,
        )

    payload_to_dump: Any
    if args.print_generate_messages_only:
        payload_to_dump = result["normalized_messages"]
    else:
        payload_to_dump = result

    output = json.dumps(
        payload_to_dump,
        ensure_ascii=False,
        indent=(2 if args.pretty else None),
        default=str,
    )
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
