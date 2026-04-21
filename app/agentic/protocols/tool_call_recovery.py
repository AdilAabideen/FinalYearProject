from __future__ import annotations

import json
from typing import Any

from .protocol_types import (
    AllowedToolNames,
    NormalizedToolCall,
    ToolCallParseResult,
    ToolCallParseSource,
)
from .tool_protocol import normalize_tool_calls


def _extract_raw_calls(parsed: Any) -> list[Any]:
    if isinstance(parsed, dict) and isinstance(parsed.get("tool_calls"), list):
        return list(parsed["tool_calls"])
    if isinstance(parsed, dict) and isinstance(parsed.get("name"), str):
        return [parsed]
    if isinstance(parsed, list):
        return parsed
    return []


def _dict_calls_to_dataclasses(
    calls: list[dict[str, Any]],
    *,
    source: ToolCallParseSource,
) -> list[NormalizedToolCall]:
    out: list[NormalizedToolCall] = []
    for call in calls:
        call_id = call.get("id")
        name = call.get("name")
        args = call.get("args", {})
        if not isinstance(call_id, str) or not isinstance(name, str):
            continue
        out.append(
            NormalizedToolCall(
                id=call_id,
                name=name,
                args=args if isinstance(args, dict) else {},
                source=source,
                recovered=True,
            )
        )
    return out


def recover_from_raw_json_text(
    content: str,
    *,
    allowed_tool_names: AllowedToolNames = None,
) -> ToolCallParseResult:
    stripped = (content or "").strip()
    if not stripped:
        return ToolCallParseResult()

    try:
        parsed = json.loads(stripped)
    except Exception:
        return ToolCallParseResult()

    raw_calls = _extract_raw_calls(parsed)
    normalized = normalize_tool_calls(raw_calls, allowed_tool_names=allowed_tool_names)
    calls = _dict_calls_to_dataclasses(normalized, source=ToolCallParseSource.TEXT_JSON)
    return ToolCallParseResult(
        calls=calls,
        succeeded=bool(calls),
        source=ToolCallParseSource.TEXT_JSON,
        recovered=bool(calls),
    )


def recover_from_fenced_json_text(
    content: str,
    *,
    allowed_tool_names: AllowedToolNames = None,
) -> ToolCallParseResult:
    stripped = (content or "").strip()
    if not (stripped.startswith("```") and stripped.endswith("```")):
        return ToolCallParseResult()

    block = stripped[3:-3].strip()
    if block.lower().startswith("json"):
        block = block[4:].strip()

    try:
        parsed = json.loads(block)
    except Exception:
        return ToolCallParseResult()

    raw_calls = _extract_raw_calls(parsed)
    normalized = normalize_tool_calls(raw_calls, allowed_tool_names=allowed_tool_names)
    calls = _dict_calls_to_dataclasses(normalized, source=ToolCallParseSource.TEXT_FENCED_JSON)
    return ToolCallParseResult(
        calls=calls,
        succeeded=bool(calls),
        source=ToolCallParseSource.TEXT_FENCED_JSON,
        recovered=bool(calls),
    )


def recover_from_jsonl_text(
    content: str,
    *,
    allowed_tool_names: AllowedToolNames = None,
) -> ToolCallParseResult:
    stripped = (content or "").strip()
    if not stripped:
        return ToolCallParseResult()

    all_lines_parsed = True
    saw_non_empty_line = False
    raw_calls: list[Any] = []

    for ln in stripped.splitlines():
        line = ln.strip()
        if not line:
            continue
        saw_non_empty_line = True
        try:
            parsed_line = json.loads(line)
        except Exception:
            all_lines_parsed = False
            continue
        raw_calls.extend(_extract_raw_calls(parsed_line))

    if not saw_non_empty_line:
        return ToolCallParseResult()

    normalized = normalize_tool_calls(raw_calls, allowed_tool_names=allowed_tool_names)
    calls = _dict_calls_to_dataclasses(normalized, source=ToolCallParseSource.TEXT_JSONL)
    return ToolCallParseResult(
        calls=calls,
        succeeded=bool(calls),
        source=ToolCallParseSource.TEXT_JSONL,
        recovered=bool(calls),
        all_lines_parsed=all_lines_parsed,
    )


def recover_tool_calls_from_content(
    content: str,
    *,
    allowed_tool_names: AllowedToolNames = None,
) -> ToolCallParseResult:
    raw_result = recover_from_raw_json_text(content, allowed_tool_names=allowed_tool_names)
    if raw_result.succeeded:
        return raw_result

    fenced_result = recover_from_fenced_json_text(content, allowed_tool_names=allowed_tool_names)
    if fenced_result.succeeded:
        return fenced_result

    jsonl_result = recover_from_jsonl_text(content, allowed_tool_names=allowed_tool_names)
    if jsonl_result.succeeded:
        return jsonl_result

    return ToolCallParseResult()


def to_legacy_recovery_output(
    result: ToolCallParseResult,
) -> tuple[list[dict[str, Any]], bool]:
    calls = [
        {
            "id": call.id,
            "name": call.name,
            "args": call.args,
            "type": "tool_call",
        }
        for call in result.calls
    ]
    if not calls:
        return [], False

    if result.source == ToolCallParseSource.TEXT_JSONL and result.all_lines_parsed is not None:
        return calls, bool(result.all_lines_parsed)

    return calls, True
