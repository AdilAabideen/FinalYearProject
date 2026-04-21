from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


AllowedToolNames = set[str] | None


class ToolCallParseSource(str, Enum):
    """Origin category for a parsed tool call."""

    NATIVE_TOOL_CALLS = "native_tool_calls"
    PROVIDER_METADATA = "provider_metadata"
    FUNCTION_CALL = "function_call"
    TEXT_JSON = "text_json"
    TEXT_FENCED_JSON = "text_fenced_json"
    TEXT_JSONL = "text_jsonl"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NormalizedToolCall:
    """Provider-agnostic normalized tool call payload."""

    id: str
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    # Per-call provenance enables mixed-source batches to be represented.
    source: ToolCallParseSource = ToolCallParseSource.UNKNOWN
    # True when this call came from textual/heuristic recovery.
    recovered: bool = False


@dataclass(frozen=True)
class ToolCallParseResult:
    """Result bundle returned by tool-call parsing/recovery."""

    calls: list[NormalizedToolCall] = field(default_factory=list)
    # Optional batch-level summary. Use `None` when calls have mixed provenance.
    source: ToolCallParseSource | None = ToolCallParseSource.UNKNOWN
    recovered: bool | None = False
