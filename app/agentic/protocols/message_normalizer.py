from __future__ import annotations

import json
from typing import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage


def normalize_chat_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Normalize provider chat messages for deterministic role sequencing.

    Rules:
    - Merge all system content into one leading system message.
    - Merge consecutive turns that share the same role.
    - Preserve relative order of non-system turns.
    """
    system_parts: list[str] = []
    normalized: list[dict[str, str]] = []

    for msg in messages:
        role = str(msg.get("role") or "").strip()
        content = str(msg.get("content") or "").strip()
        if not role:
            continue

        if role == "system":
            if content:
                system_parts.append(content)
            continue

        if normalized and normalized[-1].get("role") == role:
            prev = str(normalized[-1].get("content") or "").strip()
            if prev and content:
                normalized[-1]["content"] = f"{prev}\n\n{content}"
            elif content:
                normalized[-1]["content"] = content
            continue

        normalized.append({"role": role, "content": content})

    if system_parts:
        normalized = [{"role": "system", "content": "\n\n".join(system_parts)}] + normalized

    return normalized


def to_provider_messages(
    messages: Sequence[BaseMessage],
    *,
    allow_tool_messages: bool = False,
    tool_message_error: str,
    unsupported_type_label: str,
) -> list[dict[str, str]]:
    """Render LangChain messages into provider chat-message dicts."""
    out: list[dict[str, str]] = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        elif isinstance(msg, ToolMessage):
            if not allow_tool_messages:
                raise ValueError(tool_message_error)
            role = "user"
        else:
            raise ValueError(f"Unsupported message type for {unsupported_type_label}: {type(msg).__name__}")

        if isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", None) or "tool"
            tool_status = getattr(msg, "status", None) or "success"
            tool_id = getattr(msg, "tool_call_id", None) or "unknown"
            raw_content = (getattr(msg, "content", None) or "").strip()
            content = f"Tool result ({tool_name}, id={tool_id}, status={tool_status}):\n{raw_content}"
        else:
            content = (getattr(msg, "content", None) or "").strip()
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                tool_calls = [
                    {
                        "id": tc.get("id"),
                        "name": tc.get("name"),
                        "arguments": tc.get("args", {}),
                    }
                    for tc in msg.tool_calls
                ]
                rendered_calls = json.dumps({"tool_calls": tool_calls}, ensure_ascii=False)
                content = f"{content}\n\n{rendered_calls}" if content else rendered_calls
        out.append({"role": role, "content": content})
    return out
