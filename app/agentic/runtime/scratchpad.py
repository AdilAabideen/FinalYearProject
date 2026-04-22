from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from app.agentic.protocols import to_provider_messages
from app.agentic.telemetry import TokenEstimator


@dataclass(frozen=True)
class ScratchpadConfig:
    """Policy toggles for scratchpad contents."""

    include_final_assistant_output: bool = False
    include_raw_provider_debug: bool = False
    compact_assistant_tool_calls: bool = True
    verbose: bool = False
    log_token_estimates: bool = True
    log_message_preview: bool = True
    log_message_max_chars: int = 4000
    log_prefix: str = "[scratchpad]"
    on_message_appended: Callable[[dict[str, Any]], None] | None = None


class Scratchpad:
    """
    Explicit scratchpad state contract for runtime context accumulation.

    Contract:
    - Include assistant tool-call messages.
    - Include tool results.
    - Include final assistant output only when configured.
    - Strip raw provider debug payloads unless explicitly configured.
    """

    _RAW_PROVIDER_DEBUG_KEYS = (
        "raw_tool_text",
        "raw_provider_content",
        "provider_debug",
        "provider_raw",
    )

    def __init__(
        self,
        *,
        config: ScratchpadConfig | None = None,
        token_estimator: TokenEstimator | None = None,
        log_fn: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config or ScratchpadConfig()
        self._messages: list[BaseMessage] = []
        self._token_estimator = token_estimator or TokenEstimator()
        self._log_fn = log_fn or print
        self._pending_tool_call_entries: list[dict[str, Any]] = []

    def append_assistant_tool_call(self, message: AIMessage) -> AIMessage:
        """Append an assistant message that contains one or more tool calls."""
        tool_calls = list(getattr(message, "tool_calls", []) or [])
        if not tool_calls:
            raise ValueError("append_assistant_tool_call requires AIMessage.tool_calls to be non-empty.")

        cloned = self._clone_ai_message(message)
        assistant_index = len(self._messages)
        self._messages.append(cloned)
        self._register_pending_tool_call_entry(assistant_index=assistant_index, tool_calls=tool_calls)
        self._emit_append_event(kind="assistant_tool_call", message=cloned)
        return cloned

    def append_tool_result(self, message: ToolMessage) -> ToolMessage:
        """Append a tool result message."""
        cloned = self._clone_tool_message(message)
        self._messages.append(cloned)
        self._maybe_compact_assistant_after_tool_result(cloned)
        self._emit_append_event(kind="tool_result", message=cloned)
        return cloned

    def append_final_assistant(self, message: AIMessage) -> AIMessage | None:
        """
        Optionally append final assistant output.

        Returns appended message when enabled, else returns None.
        """
        if not self.config.include_final_assistant_output:
            return None

        cloned = self._clone_ai_message(message)
        self._messages.append(cloned)
        self._emit_append_event(kind="final_assistant", message=cloned)
        return cloned

    def messages(self) -> list[BaseMessage]:
        """Return a shallow copy of current scratchpad messages."""
        return list(self._messages)

    def clear(self) -> None:
        """Clear scratchpad state."""
        self._messages.clear()
        if self.config.verbose:
            self._log_fn(f"{self.config.log_prefix} cleared messages=0")

    def __len__(self) -> int:
        return len(self._messages)

    def _clone_ai_message(self, message: AIMessage) -> AIMessage:
        additional_kwargs = self._sanitize_additional_kwargs(
            dict(getattr(message, "additional_kwargs", {}) or {})
        )
        return AIMessage(
            content=str(getattr(message, "content", "") or ""),
            tool_calls=list(getattr(message, "tool_calls", []) or []),
            additional_kwargs=additional_kwargs,
            response_metadata=getattr(message, "response_metadata", {}),
            id=getattr(message, "id", None),
            name=getattr(message, "name", None),
        )

    def _register_pending_tool_call_entry(self, *, assistant_index: int, tool_calls: list[Any]) -> None:
        if not self.config.compact_assistant_tool_calls:
            return

        call_ids: set[str] = set()
        call_names: list[str] = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, Mapping):
                continue
            call_id = tool_call.get("id")
            if isinstance(call_id, str) and call_id.strip():
                call_ids.add(call_id.strip())

            call_name = tool_call.get("name")
            if isinstance(call_name, str) and call_name.strip():
                call_names.append(call_name.strip())

        self._pending_tool_call_entries.append(
            {
                "assistant_index": int(assistant_index),
                "call_ids": call_ids,
                "resolved_call_ids": set(),
                "call_names": call_names,
                "compacted": False,
            }
        )

    def _maybe_compact_assistant_after_tool_result(self, tool_message: ToolMessage) -> None:
        if not self.config.compact_assistant_tool_calls:
            return

        tool_call_id = getattr(tool_message, "tool_call_id", None)
        if not isinstance(tool_call_id, str) or not tool_call_id.strip():
            return
        tool_call_id = tool_call_id.strip()

        for entry in self._pending_tool_call_entries:
            if entry.get("compacted"):
                continue

            call_ids = entry.get("call_ids") or set()
            if call_ids and tool_call_id not in call_ids:
                continue

            resolved_call_ids: set[str] = entry.get("resolved_call_ids", set())
            resolved_call_ids.add(tool_call_id)
            entry["resolved_call_ids"] = resolved_call_ids

            should_compact = False
            if call_ids:
                should_compact = resolved_call_ids.issuperset(call_ids)
            else:
                # Fallback for missing IDs: compact on first matching result.
                should_compact = True

            if should_compact:
                self._compact_assistant_entry(entry)
            break

    def _compact_assistant_entry(self, entry: Mapping[str, Any]) -> None:
        assistant_index = int(entry.get("assistant_index", -1))
        if assistant_index < 0 or assistant_index >= len(self._messages):
            return
        current = self._messages[assistant_index]
        if not isinstance(current, AIMessage):
            return

        call_names = [str(name) for name in (entry.get("call_names") or []) if str(name)]
        if len(call_names) == 1:
            compact_content = f"[Tool Call] {call_names[0]}"
        else:
            compact_content = f"[Tool Calls] {', '.join(call_names)}" if call_names else "[Tool Call]"

        additional_kwargs = self._sanitize_additional_kwargs(
            dict(getattr(current, "additional_kwargs", {}) or {})
        )
        compacted = AIMessage(
            content=compact_content,
            tool_calls=[],
            additional_kwargs=additional_kwargs,
            response_metadata=getattr(current, "response_metadata", {}),
            id=getattr(current, "id", None),
            name=getattr(current, "name", None),
        )
        self._messages[assistant_index] = compacted
        if isinstance(entry, dict):
            entry["compacted"] = True

        if self.config.verbose:
            self._log_fn(
                f"{self.config.log_prefix} compacted assistant_index={assistant_index} content={compact_content}"
            )
        if self.config.on_message_appended is not None:
            self.config.on_message_appended(
                {
                    "event": "scratchpad_message_compacted",
                    "assistant_index": assistant_index,
                    "content": compact_content,
                    "message_count": len(self._messages),
                }
            )

    @staticmethod
    def _clone_tool_message(message: ToolMessage) -> ToolMessage:
        kwargs: dict[str, Any] = {
            "content": str(getattr(message, "content", "") or ""),
            "tool_call_id": getattr(message, "tool_call_id", None),
            "name": getattr(message, "name", None),
            "status": getattr(message, "status", None),
        }
        if hasattr(message, "artifact"):
            kwargs["artifact"] = getattr(message, "artifact")
        return ToolMessage(**kwargs)

    def _sanitize_additional_kwargs(self, additional_kwargs: Mapping[str, Any]) -> dict[str, Any]:
        if self.config.include_raw_provider_debug:
            return dict(additional_kwargs)

        sanitized = dict(additional_kwargs)
        for key in self._RAW_PROVIDER_DEBUG_KEYS:
            sanitized.pop(key, None)
        return sanitized

    def _emit_append_event(self, *, kind: str, message: BaseMessage) -> None:
        if not (self.config.verbose or self.config.on_message_appended is not None):
            return

        msg_tokens: int | None = None
        total_tokens: int | None = None
        if self.config.log_token_estimates:
            msg_tokens = self._token_estimator.estimate_messages_tokens([message])
            total_tokens = self._token_estimator.estimate_messages_tokens(self._messages)

        payload = {
            "event": "scratchpad_message_appended",
            "kind": kind,
            "role": self._message_role(message),
            "message_count": len(self._messages),
            "message_tokens_estimate": msg_tokens,
            "scratchpad_tokens_estimate": total_tokens,
            "provider_preview": self._provider_preview(message),
        }

        if self.config.verbose:
            self._log_fn(
                f"{self.config.log_prefix} append kind={kind} role={payload['role']} "
                f"messages={payload['message_count']} msg_tokens={msg_tokens} total_tokens={total_tokens}"
            )
            if self.config.log_message_preview and payload["provider_preview"] is not None:
                preview = str(payload["provider_preview"])
                max_chars = max(1, int(self.config.log_message_max_chars))
                if len(preview) > max_chars:
                    preview = preview[:max_chars] + "…(truncated)"
                self._log_fn(f"{self.config.log_prefix} message {preview}")

        if self.config.on_message_appended is not None:
            self.config.on_message_appended(payload)

    @staticmethod
    def _message_role(message: BaseMessage) -> str:
        if isinstance(message, AIMessage):
            return "assistant"
        if isinstance(message, ToolMessage):
            return "tool"
        return type(message).__name__.lower()

    @staticmethod
    def _provider_preview(message: BaseMessage) -> str | None:
        """Render one-message preview in provider message format."""
        try:
            rendered = to_provider_messages(
                [message],
                allow_tool_messages=True,
                tool_message_error="tool messages enabled for preview rendering",
                unsupported_type_label="scratchpad-preview",
            )
        except Exception:
            return None

        if not rendered:
            return None
        role = str(rendered[0].get("role") or "")
        content = str(rendered[0].get("content") or "")
        return f"role={role} content={content}"
