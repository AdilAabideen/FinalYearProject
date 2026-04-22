from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import AIMessage

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


def _extract_balanced_json_segment(
    text: str,
    *,
    open_char: str,
    close_char: str,
    start_index: int,
) -> str | None:
    """Extract first balanced JSON-like segment from `start_index`."""
    if start_index < 0 or start_index >= len(text):
        return None
    if text[start_index] != open_char:
        return None

    depth = 0
    in_string = False
    escaped = False
    for i in range(start_index, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == open_char:
            depth += 1
            continue
        if ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start_index : i + 1]

    return None


def recover_from_partial_json_text(
    content: str,
    *,
    allowed_tool_names: AllowedToolNames = None,
) -> ToolCallParseResult:
    """
    Recover from partial JSON by extracting first balanced object and parsing it.

    Useful when output contains valid tool-call JSON plus trailing garbage.
    """
    stripped = (content or "").strip()
    if not stripped:
        return ToolCallParseResult()

    first_obj_start = stripped.find("{")
    if first_obj_start < 0:
        return ToolCallParseResult()

    candidate = _extract_balanced_json_segment(
        stripped,
        open_char="{",
        close_char="}",
        start_index=first_obj_start,
    )
    if not candidate:
        return ToolCallParseResult()

    try:
        parsed = json.loads(candidate)
    except Exception:
        return ToolCallParseResult()

    raw_calls = _extract_raw_calls(parsed)
    normalized = normalize_tool_calls(raw_calls, allowed_tool_names=allowed_tool_names)
    calls = _dict_calls_to_dataclasses(normalized, source=ToolCallParseSource.TEXT_PARTIAL_JSON)
    return ToolCallParseResult(
        calls=calls,
        succeeded=bool(calls),
        source=ToolCallParseSource.TEXT_PARTIAL_JSON,
        recovered=bool(calls),
    )


def recover_from_tool_calls_array_text(
    content: str,
    *,
    allowed_tool_names: AllowedToolNames = None,
) -> ToolCallParseResult:
    """
    Recover by extracting a balanced `tool_calls` array and wrapping it as JSON.

    Useful when the model emits malformed object wrappers but the `tool_calls` array
    itself is still syntactically valid.
    """
    stripped = (content or "").strip()
    if not stripped:
        return ToolCallParseResult()

    key_match = re.search(r'"tool_calls"\s*:', stripped)
    if not key_match:
        return ToolCallParseResult()

    array_start = stripped.find("[", key_match.end())
    if array_start < 0:
        return ToolCallParseResult()

    array_segment = _extract_balanced_json_segment(
        stripped,
        open_char="[",
        close_char="]",
        start_index=array_start,
    )
    if not array_segment:
        return ToolCallParseResult()

    candidate = f'{{"tool_calls":{array_segment}}}'
    try:
        parsed = json.loads(candidate)
    except Exception:
        return ToolCallParseResult()

    raw_calls = _extract_raw_calls(parsed)
    normalized = normalize_tool_calls(raw_calls, allowed_tool_names=allowed_tool_names)
    calls = _dict_calls_to_dataclasses(normalized, source=ToolCallParseSource.TEXT_TOOL_CALLS_ARRAY)
    return ToolCallParseResult(
        calls=calls,
        succeeded=bool(calls),
        source=ToolCallParseSource.TEXT_TOOL_CALLS_ARRAY,
        recovered=bool(calls),
    )


def recover_tool_calls_from_content(
    content: str,
    *,
    allowed_tool_names: AllowedToolNames = None,
) -> ToolCallParseResult:
    fenced_result = recover_from_fenced_json_text(content, allowed_tool_names=allowed_tool_names)
    if fenced_result.succeeded:
        return fenced_result

    raw_result = recover_from_raw_json_text(content, allowed_tool_names=allowed_tool_names)
    if raw_result.succeeded:
        return raw_result

    partial_result = recover_from_partial_json_text(content, allowed_tool_names=allowed_tool_names)
    if partial_result.succeeded:
        return partial_result

    tool_calls_array_result = recover_from_tool_calls_array_text(
        content,
        allowed_tool_names=allowed_tool_names,
    )
    if tool_calls_array_result.succeeded:
        return tool_calls_array_result

    jsonl_result = recover_from_jsonl_text(content, allowed_tool_names=allowed_tool_names)
    if jsonl_result.succeeded:
        return jsonl_result

    return ToolCallParseResult()


def looks_like_malformed_tool_call_content(
    content: str,
    *,
    allowed_tool_names: AllowedToolNames = None,
) -> bool:
    """
    Heuristic detector for malformed tool-call intent.

    Returns True only when content strongly suggests tool-call intent but could not be
    parsed/recovered into normalized calls.
    """
    text = (content or "").strip()
    if not text:
        return False

    if recover_tool_calls_from_content(text, allowed_tool_names=allowed_tool_names).succeeded:
        return False

    lowered = text.lower()
    if '"tool_calls"' in lowered or "'tool_calls'" in lowered:
        return True

    if "arguments" in lowered or '"name"' in lowered:
        if allowed_tool_names:
            lowered_names = {str(n).lower() for n in allowed_tool_names}
            if any(name in lowered for name in lowered_names):
                return True

    return False


def extract_tool_calls_with_priority(
    message: AIMessage,
    *,
    allowed_tool_names: AllowedToolNames = None,
    allow_text_recovery: bool = True,
) -> ToolCallParseResult:
    """Parse tool calls using a deterministic global priority order.

    Priority:
    1) native `message.tool_calls`
    2) provider metadata `additional_kwargs.tool_calls`
    3) provider metadata `additional_kwargs.function_call`
    4) text recovery from fenced/raw JSON
    5) text recovery from JSONL
    """

    native_calls = normalize_tool_calls(
        list(getattr(message, "tool_calls", []) or []),
        allowed_tool_names=allowed_tool_names,
    )
    if native_calls:
        return ToolCallParseResult(
            calls=_dict_calls_to_dataclasses(native_calls, source=ToolCallParseSource.NATIVE_TOOL_CALLS),
            succeeded=True,
            source=ToolCallParseSource.NATIVE_TOOL_CALLS,
            recovered=False,
        )

    additional = getattr(message, "additional_kwargs", {}) or {}
    additional_tool_calls = additional.get("tool_calls")
    metadata_calls = normalize_tool_calls(
        additional_tool_calls,
        allowed_tool_names=allowed_tool_names,
    )
    if metadata_calls:
        return ToolCallParseResult(
            calls=_dict_calls_to_dataclasses(metadata_calls, source=ToolCallParseSource.PROVIDER_METADATA),
            succeeded=True,
            source=ToolCallParseSource.PROVIDER_METADATA,
            recovered=False,
        )

    function_call = additional.get("function_call")
    function_calls = normalize_tool_calls(
        [{"function": function_call}] if isinstance(function_call, dict) else [],
        allowed_tool_names=allowed_tool_names,
    )
    if function_calls:
        return ToolCallParseResult(
            calls=_dict_calls_to_dataclasses(function_calls, source=ToolCallParseSource.FUNCTION_CALL),
            succeeded=True,
            source=ToolCallParseSource.FUNCTION_CALL,
            recovered=False,
        )

    if not allow_text_recovery:
        return ToolCallParseResult()

    content = str(getattr(message, "content", "") or "")
    recovered = recover_tool_calls_from_content(content, allowed_tool_names=allowed_tool_names)
    if recovered.succeeded:
        return recovered
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
