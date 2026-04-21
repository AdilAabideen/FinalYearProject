from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from queue import Queue
from typing import Any, AsyncGenerator, Callable, Iterable, Mapping, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool as lc_tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict

from app.agentic.protocols import AllowedToolNames, NormalizedToolCall, ToolCallParseResult
from app.agentic.runtime.agent_runner import AgentRunner
from app.agentic.runtime.finalization_policy import FinalizationPolicy
from app.agentic.runtime.runtime_config import RuntimeConfig
from app.agentic.runtime.tool_executor import ToolExecutionTrace, ToolExecutor

try:
    import tiktoken
except Exception:  # pragma: no cover - optional dependency at runtime
    tiktoken = None


@dataclass
class LLMCallMetric:
    run_id: str
    agent_name: str
    call_index: int
    iteration: int
    call_kind: str
    model_name: str | None
    started_at: datetime
    ended_at: datetime
    latency_ms: int
    input_tokens: int
    output_tokens: int
    tokens_total: int
    usage_source: str
    had_tool_calls: bool
    tool_call_count: int
    tool_names: list[str] = field(default_factory=list)
    error_text: str | None = None


@dataclass
class ToolExecutionMetric:
    run_id: str
    agent_name: str
    iteration: int
    tool_call_id: str
    tool_name: str
    started_at: datetime
    ended_at: datetime
    latency_ms: int
    status: str
    result_char_count: int
    result_estimated_tokens: int
    error_text: str | None = None


class TokenEstimator:
    """Token estimation helper with canonical serialization for messages and outputs."""

    def estimate_text_tokens(self, text: str) -> int:
        content = text or ""
        if not content:
            return 0

        if tiktoken is not None:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
                return len(enc.encode(content))
            except Exception:
                pass

        return max(1, len(content) // 4)

    def estimate_messages_tokens(self, messages: list[BaseMessage]) -> int:
        serialized = [self.serialize_message_for_estimation(msg) for msg in messages]
        return self.estimate_text_tokens("\n".join(serialized))

    def estimate_ai_output_tokens(self, msg: AIMessage) -> int:
        return self.estimate_text_tokens(self.serialize_ai_output_for_estimation(msg))

    def estimate_tool_result_tokens(self, content: str) -> int:
        return self.estimate_text_tokens(content)

    def estimate_jsonable_output_tokens(self, value: Any) -> int:
        return self.estimate_text_tokens(self._json_dumps(self._to_jsonable(value)))

    def serialize_message_for_estimation(self, message: BaseMessage) -> str:
        canonical = self._canonical_message(message)
        return self._json_dumps(canonical)

    def serialize_ai_output_for_estimation(self, message: AIMessage) -> str:
        canonical = {
            "content": self._normalize_content(getattr(message, "content", "")),
        }

        tool_calls = self._canonical_tool_calls(list(getattr(message, "tool_calls", []) or []))
        if tool_calls:
            canonical["tool_calls"] = tool_calls

        fn = self._extract_function_call_fields(getattr(message, "additional_kwargs", {}) or {})
        if fn:
            canonical.update(fn)

        return self._json_dumps(canonical)

    @staticmethod
    def _json_dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _normalize_content(content: Any) -> Any:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            normalized_parts: list[dict[str, Any]] = []
            for item in content:
                if isinstance(item, str):
                    normalized_parts.append({"type": "text", "text": item})
                    continue

                if not isinstance(item, Mapping):
                    continue

                part_type = str(item.get("type") or "")
                if part_type == "text":
                    normalized_parts.append({"type": "text", "text": str(item.get("text") or "")})
                elif part_type in {"image_url", "input_image"}:
                    url = item.get("image_url")
                    if isinstance(url, Mapping):
                        url = url.get("url")
                    normalized_parts.append({"type": part_type, "url": str(url or "")})
                elif part_type:
                    normalized_parts.append({"type": part_type})

            return normalized_parts

        return str(content)

    def _canonical_message(self, message: BaseMessage) -> dict[str, Any]:
        role = self._message_role(message)
        payload: dict[str, Any] = {
            "role": role,
            "content": self._normalize_content(getattr(message, "content", "")),
        }

        if isinstance(message, AIMessage): # Role is AI Message
            tool_calls = self._canonical_tool_calls(list(getattr(message, "tool_calls", []) or []))
            if tool_calls:
                payload["tool_calls"] = tool_calls

            fn = self._extract_function_call_fields(getattr(message, "additional_kwargs", {}) or {})
            if fn:
                payload.update(fn)

        if isinstance(message, ToolMessage):
            payload.update(
                {
                    "name": getattr(message, "name", None),
                    "status": getattr(message, "status", None),
                    "tool_call_id": getattr(message, "tool_call_id", None),
                }
            )

        return payload

    @staticmethod
    def _message_role(message: BaseMessage) -> str:
        if isinstance(message, SystemMessage):
            return "system"
        if isinstance(message, HumanMessage):
            return "user"
        if isinstance(message, ToolMessage):
            return "tool"
        if isinstance(message, AIMessage):
            return "assistant"
        return type(message).__name__.lower()

    @staticmethod
    def _canonical_tool_calls(raw_calls: list[Any]) -> list[dict[str, Any]]:
        canonical: list[dict[str, Any]] = []
        for item in raw_calls:
            if not isinstance(item, Mapping):
                continue

            name = item.get("name")
            args = item.get("args", item.get("arguments", {}))
            call_id = item.get("id") or item.get("tool_call_id")

            if not name and isinstance(item.get("function"), Mapping):
                fn = item["function"]
                name = fn.get("name")
                args = fn.get("arguments", args)

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {"raw_arguments": args}

            if not isinstance(args, Mapping):
                args = {"value": args}

            if name:
                canonical.append(
                    {
                        "id": str(call_id) if call_id is not None else None,
                        "name": str(name),
                        "args": dict(args),
                    }
                )

        return canonical

    def _extract_function_call_fields(self, additional_kwargs: Mapping[str, Any]) -> dict[str, Any]:
        fields: dict[str, Any] = {}

        function_call = additional_kwargs.get("function_call")
        if isinstance(function_call, Mapping):
            fields["function_call"] = {
                "name": function_call.get("name"),
                "arguments": function_call.get("arguments"),
            }

        tool_calls = additional_kwargs.get("tool_calls")
        if isinstance(tool_calls, list):
            canonical = self._canonical_tool_calls(tool_calls)
            if canonical:
                fields["provider_tool_calls"] = canonical

        return fields

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if hasattr(value, "model_dump") and callable(value.model_dump):
            try:
                return value.model_dump()
            except Exception:
                pass
        if isinstance(value, Mapping):
            return dict(value)
        if isinstance(value, (list, tuple)):
            return list(value)
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)


class EventEmitter:
    """Emit run events in the existing persistence shape with monotonic sequence IDs."""

    def __init__(self) -> None:
        self._handlers: list[Callable[[dict[str, Any]], None]] = []
        self._run_id: str | None = None
        self._agent_name: str | None = None
        self._seq: int = 0

    def set_context(self, *, run_id: str, agent_name: str, start_seq: int = 0) -> None:
        self._run_id = str(run_id)
        self._agent_name = str(agent_name)
        self._seq = int(start_seq)

    def set_handlers(self, handlers: Sequence[Callable[[dict[str, Any]], None]] | None) -> None:
        self._handlers = list(handlers or [])

    def add_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        self._handlers.append(handler)

    def emit(
        self,
        *,
        event_type: str,
        node_name: str | None = None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        status: str | None = None,
        payload_json: dict[str, Any] | None = None,
        payload_text: str | None = None,
    ) -> None:
        if not self._handlers or self._run_id is None or self._agent_name is None:
            return

        self._seq += 1
        payload = {
            "run_id": self._run_id,
            "agent_name": self._agent_name,
            "seq": self._seq,
            "event_type": event_type,
            "node_name": node_name,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "status": status,
            "payload_json": payload_json,
            "payload_text": payload_text,
        }
        for handler in self._handlers:
            handler(payload)


class TelemetryEmitter:
    """Emit structured LLM and tool metrics through adapter handlers."""

    def __init__(self) -> None:
        self._llm_handlers: list[Callable[[dict[str, Any]], None]] = []
        self._tool_handlers: list[Callable[[dict[str, Any]], None]] = []
        self._run_id: str | None = None
        self._agent_name: str | None = None
        self._call_index: int = 0

    def set_context(self, *, run_id: str, agent_name: str) -> None:
        self._run_id = str(run_id)
        self._agent_name = str(agent_name)
        self._call_index = 0

    def set_llm_handlers(self, handlers: Sequence[Callable[[dict[str, Any]], None]] | None) -> None:
        self._llm_handlers = list(handlers or [])

    def add_llm_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        self._llm_handlers.append(handler)

    def set_tool_handlers(self, handlers: Sequence[Callable[[dict[str, Any]], None]] | None) -> None:
        self._tool_handlers = list(handlers or [])

    def add_tool_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        self._tool_handlers.append(handler)

    def next_call_index(self) -> int:
        self._call_index += 1
        return self._call_index

    def current_context(self) -> tuple[str | None, str | None]:
        return self._run_id, self._agent_name

    def emit_llm(self, metric: LLMCallMetric) -> None:
        if not self._llm_handlers:
            return
        payload = asdict(metric)
        for handler in self._llm_handlers:
            handler(payload)

    def emit_tool(self, metric: ToolExecutionMetric) -> None:
        if not self._tool_handlers:
            return
        payload = asdict(metric)
        for handler in self._tool_handlers:
            handler(payload)


class SSEHandrolledAgent:
    """Lightweight hand-rolled tool agent with create_react_agent-like stream outputs.

    Stream yields `(mode, data)` tuples where:
    - mode == "updates" -> {node_name: {"messages": [message, ...]}}
    - mode == "values" -> full evolving state dict
    """

    def __init__(
        self,
        model: str | Any = "gpt-4o-mini",
        tools: Sequence[Any] | None = None,
        system_prompt: str = "You are a helpful assistant.",
        response_format: dict[str, Any] | type[BaseModel] | None = None,
        *,
        final_answer_tool_name: str | None = "final_answer",
        llm_kwargs: dict[str, Any] | None = None,
        agent_node_name: str = "agent",
        tools_node_name: str = "tools",
        run_timeout_s: float | None = None,
        event_handlers: Sequence[Callable[[dict[str, Any]], None]] | None = None,
        llm_call_handlers: Sequence[Callable[[dict[str, Any]], None]] | None = None,
        tool_call_handlers: Sequence[Callable[[dict[str, Any]], None]] | None = None,
        max_tool_calls: int = 2,
        runtime_config: RuntimeConfig | None = None,
    ) -> None:
        self.model = self._build_model(model=model, llm_kwargs=llm_kwargs)
        self.tools: list[BaseTool] = self._coerce_tools(tools or [])

        self.system_prompt = (
            system_prompt if isinstance(system_prompt, str) and system_prompt.strip() else "You are a helpful assistant."
        )
        self.response_format = response_format
        self.final_answer_tool_name = final_answer_tool_name

        if self.final_answer_tool_name and self.response_format is not None:
            existing = {t.name for t in self.tools}
            if self.final_answer_tool_name not in existing:
                self.tools.append(self._build_final_answer_tool())

        self.tools_by_name: dict[str, BaseTool] = {t.name: t for t in self.tools}
        self.agent_node_name = agent_node_name
        self.tools_node_name = tools_node_name
        self.run_timeout_s = None if run_timeout_s is None else float(run_timeout_s)
        if not isinstance(max_tool_calls, int):
            raise TypeError("max_tool_calls must be an integer.")
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be >= 1.")
        if runtime_config is not None and not isinstance(runtime_config, RuntimeConfig):
            raise TypeError("runtime_config must be a RuntimeConfig instance when provided.")
        self.runtime_config = runtime_config or RuntimeConfig(
            max_tool_calls_per_turn=max_tool_calls,
            require_final_answer_tool=True,
            allow_text_tool_recovery=True,
            allow_plain_json_final_output=True,
            drop_extra_tool_calls=True,
        )
        self.max_tool_calls = int(self.runtime_config.max_tool_calls_per_turn)
        self._token_estimator = TokenEstimator()
        self._events = EventEmitter()
        self._telemetry = TelemetryEmitter()
        self._finalization_policy = FinalizationPolicy(
            config=self.runtime_config,
            final_answer_tool_name=self.final_answer_tool_name,
        )
        self._tool_executor = ToolExecutor(
            tools_by_name=self.tools_by_name,
            estimate_tool_result_tokens=self._token_estimator.estimate_tool_result_tokens,
            emit_trace=self._emit_tool_execution_trace,
        )

        self.set_event_handlers(event_handlers)
        self.set_llm_call_handlers(llm_call_handlers)
        self.set_tool_call_handlers(tool_call_handlers)

        if self.tools:
            self.bound_model = self.model.bind_tools(self.tools, tool_choice="any")
        else:
            self.bound_model = self.model
        self._agent_runner = AgentRunner(
            bound_model=self.bound_model,
            runtime_config=self.runtime_config,
            run_timeout_s=self.run_timeout_s,
            agent_node_name=self.agent_node_name,
            tools_node_name=self.tools_node_name,
            finalization_policy=self._finalization_policy,
            tool_executor=self._tool_executor,
            current_telemetry_context=self._telemetry.current_context,
            render_system_prompt=self._render_system_prompt,
            payload_to_human_content=self._payload_to_human_content,
            ainvoke_with_telemetry=self._ainvoke_with_telemetry,
            normalize_tool_call=self._normalize_tool_call,
            recover_tool_calls_from_content=self._recover_tool_calls_from_content,
            ai_message_with_tool_calls=self._ai_message_with_tool_calls,
            limit_tool_calls=self._limit_tool_calls,
            json_from_text=self._json_from_text,
            parsed_to_payload_json=self._parsed_to_payload_json,
            emit_event=self._emit_event,
            values_state=self._values_state,
        )

    @staticmethod
    def _build_model(model: str | Any, llm_kwargs: dict[str, Any] | None) -> Any:
        if isinstance(model, str):
            kwargs = {"model": model, "temperature": 0.0}
            if llm_kwargs:
                kwargs.update(llm_kwargs)
            return ChatOpenAI(**kwargs)
        return model

    @staticmethod
    def _coerce_tools(raw_tools: Sequence[Any]) -> list[BaseTool]:
        normalized: list[BaseTool] = []
        for item in raw_tools:
            if isinstance(item, BaseTool):
                normalized.append(item)
            elif callable(item):
                normalized.append(lc_tool(item))
            else:
                raise TypeError(f"Unsupported tool type: {type(item)!r}")
        return normalized

    @staticmethod
    def _fallback_final_answer_schema() -> type[BaseModel]:
        class FinalAnswerPayload(BaseModel):
            model_config = ConfigDict(extra="allow")

        return FinalAnswerPayload

    def _build_final_answer_tool(self) -> BaseTool:
        if not self.final_answer_tool_name:
            raise ValueError("final_answer_tool_name must be set to build final_answer tool.")

        strict_schema = isinstance(self.response_format, type) and issubclass(self.response_format, BaseModel)
        schema_model = self.response_format if strict_schema else self._fallback_final_answer_schema()
        tool_name = self.final_answer_tool_name

        @lc_tool(tool_name, args_schema=schema_model)
        def _final_answer(**kwargs: Any) -> dict[str, Any]:
            """Signal completion and return the final structured payload."""
            if not kwargs:
                raise ValueError("final_answer requires a non-empty JSON object.")

            if strict_schema:
                validated = schema_model.model_validate(kwargs)
                return validated.model_dump()

            return dict(kwargs)

        return _final_answer

    def _render_system_prompt(self) -> str:
        return self.system_prompt

    @staticmethod
    def _payload_to_human_content(payload: Any) -> str:
        if isinstance(payload, str):
            return payload

        if isinstance(payload, Mapping) and isinstance(payload.get("input"), str):
            return str(payload["input"])

        if isinstance(payload, Mapping) and isinstance(payload.get("messages"), list):
            for item in reversed(payload["messages"]):
                if isinstance(item, tuple) and len(item) == 2 and str(item[0]).lower() == "user":
                    return str(item[1])
                if isinstance(item, Mapping) and str(item.get("role", "")).lower() == "user":
                    return str(item.get("content", ""))
                if isinstance(item, HumanMessage):
                    return str(item.content or "")

        return json.dumps(payload, default=str, ensure_ascii=False)

    @staticmethod
    def _json_from_text(text: str) -> tuple[Any | None, str]:
        raw = (text or "").strip()
        if not raw:
            return None, raw

        try:
            return json.loads(raw), raw
        except Exception:
            return None, raw

    @staticmethod
    def _iter_json_objects(text: str) -> Iterable[Any]:
        decoder = json.JSONDecoder()
        idx = 0
        n = len(text)
        while idx < n:
            while idx < n and text[idx].isspace():
                idx += 1
            if idx >= n:
                break

            if text[idx] not in "[{":
                idx += 1
                continue

            try:
                obj, end = decoder.raw_decode(text, idx)
                yield obj
                idx = end
            except json.JSONDecodeError:
                idx += 1

    @classmethod
    def _normalize_tool_call(cls, obj: Mapping[str, Any]) -> dict[str, Any] | None:
        # TODO(protocol-types): return NormalizedToolCall once runtime logic is migrated.
        name = obj.get("name") or obj.get("tool_name")
        args = obj.get("args", obj.get("arguments", {}))
        call_id = obj.get("id") or obj.get("tool_call_id") or f"call_{uuid.uuid4().hex[:24]}"

        function = obj.get("function")
        if not name and isinstance(function, Mapping):
            name = function.get("name")
            args = function.get("arguments", args)

        if not name:
            return None

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}

        if not isinstance(args, Mapping):
            args = {}

        return {
            "id": str(call_id),
            "name": str(name),
            "args": dict(args),
        }

    @classmethod
    def _recover_tool_calls_from_content(cls, content: str) -> list[dict[str, Any]]:
        # TODO(protocol-types): return ToolCallParseResult with parse-source metadata.
        recovered: list[dict[str, Any]] = []

        for obj in cls._iter_json_objects(content):
            if isinstance(obj, Mapping):
                tool_calls = obj.get("tool_calls")
                if isinstance(tool_calls, list):
                    for item in tool_calls:
                        if isinstance(item, Mapping):
                            normalized = cls._normalize_tool_call(item)
                            if normalized:
                                recovered.append(normalized)
                else:
                    normalized = cls._normalize_tool_call(obj)
                    if normalized:
                        recovered.append(normalized)

            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, Mapping):
                        normalized = cls._normalize_tool_call(item)
                        if normalized:
                            recovered.append(normalized)

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in recovered:
            call_id = item["id"]
            if call_id in seen:
                continue
            seen.add(call_id)
            deduped.append(item)

        return deduped

    @classmethod
    def _extract_provider_tool_calls(cls, msg: AIMessage) -> list[dict[str, Any]]:
        # TODO(protocol-types): return ToolCallParseResult and normalized dataclass calls.
        primary = list(getattr(msg, "tool_calls", []) or [])
        normalized_primary: list[dict[str, Any]] = []
        for item in primary:
            if isinstance(item, Mapping):
                normalized = cls._normalize_tool_call(item)
                if normalized:
                    normalized_primary.append(normalized)

        if normalized_primary:
            return normalized_primary

        additional = getattr(msg, "additional_kwargs", {}) or {}
        additional_tool_calls = additional.get("tool_calls")
        normalized_additional: list[dict[str, Any]] = []
        if isinstance(additional_tool_calls, list):
            for item in additional_tool_calls:
                if isinstance(item, Mapping):
                    normalized = cls._normalize_tool_call(item)
                    if normalized:
                        normalized_additional.append(normalized)
        if normalized_additional:
            return normalized_additional

        function_call = additional.get("function_call")
        if isinstance(function_call, Mapping):
            normalized = cls._normalize_tool_call({"function": function_call, "id": None})
            if normalized:
                return [normalized]

        recovered = cls._recover_tool_calls_from_content(str(msg.content or ""))
        return recovered

    @staticmethod
    def _ai_message_with_tool_calls(
        source: AIMessage,
        tool_calls: list[dict[str, Any]],
        *,
        extra_additional_kwargs: Mapping[str, Any] | None = None,
    ) -> AIMessage:
        additional_kwargs = dict(getattr(source, "additional_kwargs", {}) or {})
        if extra_additional_kwargs:
            additional_kwargs.update(dict(extra_additional_kwargs))
        return AIMessage(
            content="",
            tool_calls=list(tool_calls),
            additional_kwargs=additional_kwargs,
            response_metadata=getattr(source, "response_metadata", {}),
            id=getattr(source, "id", None),
            name=getattr(source, "name", None),
        )

    def _limit_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if len(tool_calls) <= self.max_tool_calls:
            return tool_calls, []
        return tool_calls[: self.max_tool_calls], tool_calls[self.max_tool_calls :]

    def _emit_tool_execution_trace(self, trace: ToolExecutionTrace) -> None:
        if not trace.run_id or not trace.agent_name:
            return

        self._telemetry.emit_tool(
            ToolExecutionMetric(
                run_id=trace.run_id,
                agent_name=trace.agent_name,
                iteration=trace.iteration,
                tool_call_id=trace.tool_call_id,
                tool_name=trace.tool_name,
                started_at=trace.started_at,
                ended_at=trace.ended_at,
                latency_ms=trace.latency_ms,
                status=trace.status,
                result_char_count=trace.result_char_count,
                result_estimated_tokens=trace.result_estimated_tokens,
                error_text=trace.error_text,
            )
        )

    @staticmethod
    def _values_state(
        messages: list[BaseMessage],
        iteration: int,
        done: bool,
        output_json: Any,
    ) -> dict[str, Any]:
        return {
            "messages": list(messages),
            "iteration": iteration,
            "done": done,
            "output": output_json,
        }

    def set_event_context(self, *, run_id: str, agent_name: str, start_seq: int = 0) -> None:
        self._events.set_context(run_id=run_id, agent_name=agent_name, start_seq=start_seq)
        self._telemetry.set_context(run_id=run_id, agent_name=agent_name)

    def set_event_handlers(self, handlers: Sequence[Callable[[dict[str, Any]], None]] | None) -> None:
        self._events.set_handlers(handlers)

    def add_event_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        self._events.add_handler(handler)

    def set_llm_call_handlers(self, handlers: Sequence[Callable[[dict[str, Any]], None]] | None) -> None:
        self._telemetry.set_llm_handlers(handlers)

    def add_llm_call_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        self._telemetry.add_llm_handler(handler)

    def set_tool_call_handlers(self, handlers: Sequence[Callable[[dict[str, Any]], None]] | None) -> None:
        self._telemetry.set_tool_handlers(handlers)

    def add_tool_call_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        self._telemetry.add_tool_handler(handler)

    @staticmethod
    def _parsed_to_payload_json(parsed: Any) -> dict[str, Any] | None:
        if parsed is None:
            return None
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}

    @staticmethod
    def _usage_from_obj(obj: Any) -> tuple[int | None, int | None, int | None, str | None]:
        usage = getattr(obj, "usage_metadata", None)
        if isinstance(usage, Mapping):
            in_tok = usage.get("input_tokens")
            out_tok = usage.get("output_tokens")
            tot_tok = usage.get("total_tokens")
            if in_tok is not None or out_tok is not None or tot_tok is not None:
                return (
                    int(in_tok or 0),
                    int(out_tok or 0),
                    int(tot_tok) if tot_tok is not None else int((in_tok or 0) + (out_tok or 0)),
                    "provider",
                )

        response_meta = getattr(obj, "response_metadata", None)
        if isinstance(response_meta, Mapping):
            token_usage = response_meta.get("token_usage")
            if isinstance(token_usage, Mapping):
                in_tok = token_usage.get("prompt_tokens", token_usage.get("input_tokens"))
                out_tok = token_usage.get("completion_tokens", token_usage.get("output_tokens"))
                tot_tok = token_usage.get("total_tokens")
                if in_tok is not None or out_tok is not None or tot_tok is not None:
                    return (
                        int(in_tok or 0),
                        int(out_tok or 0),
                        int(tot_tok) if tot_tok is not None else int((in_tok or 0) + (out_tok or 0)),
                        "provider",
                    )

        return None, None, None, None

    async def _ainvoke_with_telemetry(
        self,
        *,
        call_kind: str,
        iteration: int,
        messages: list[BaseMessage],
        invoke_fn: Callable[[], Any],
        timeout_s: float | None = None,
    ) -> Any:
        started_at = datetime.utcnow()
        t0 = time.perf_counter()
        model_name = getattr(self.model, "model_name", None) or getattr(self.model, "model", None)
        run_id, agent_name = self._telemetry.current_context()

        try:
            if timeout_s is None:
                response = await invoke_fn()
            else:
                response = await asyncio.wait_for(invoke_fn(), timeout=timeout_s)

            ended_at = datetime.utcnow()
            latency_ms = int((time.perf_counter() - t0) * 1000)

            in_tok, out_tok, tot_tok, usage_source = self._usage_from_obj(response)
            if in_tok is None or out_tok is None or tot_tok is None:
                in_tok = self._token_estimator.estimate_messages_tokens(messages)
                if isinstance(response, AIMessage):
                    out_tok = self._token_estimator.estimate_ai_output_tokens(response)
                else:
                    out_tok = self._token_estimator.estimate_jsonable_output_tokens(response)
                tot_tok = in_tok + out_tok
                usage_source = "estimated"

            tool_calls: list[dict[str, Any]] = []
            if isinstance(response, AIMessage):
                tool_calls = self._extract_provider_tool_calls(response)
            tool_names = [str(tc.get("name", "")) for tc in tool_calls if tc.get("name")]

            if run_id and agent_name:
                call_index = self._telemetry.next_call_index()
                self._telemetry.emit_llm(
                    LLMCallMetric(
                        run_id=run_id,
                        agent_name=agent_name,
                        call_index=call_index,
                        iteration=iteration,
                        call_kind=call_kind,
                        model_name=str(model_name) if model_name else None,
                        started_at=started_at,
                        ended_at=ended_at,
                        latency_ms=latency_ms,
                        input_tokens=int(in_tok),
                        output_tokens=int(out_tok),
                        tokens_total=int(tot_tok),
                        usage_source=str(usage_source or "estimated"),
                        had_tool_calls=bool(tool_calls),
                        tool_call_count=len(tool_calls),
                        tool_names=tool_names,
                        error_text=None,
                    )
                )

            return response
        except Exception as exc:
            normalized_exc: Exception
            if isinstance(exc, TimeoutError):
                normalized_exc = TimeoutError(str(exc) or "run_timeout_exceeded")
            else:
                normalized_exc = exc

            ended_at = datetime.utcnow()
            latency_ms = int((time.perf_counter() - t0) * 1000)
            in_tok = self._token_estimator.estimate_messages_tokens(messages)

            if run_id and agent_name:
                call_index = self._telemetry.next_call_index()
                self._telemetry.emit_llm(
                    LLMCallMetric(
                        run_id=run_id,
                        agent_name=agent_name,
                        call_index=call_index,
                        iteration=iteration,
                        call_kind=call_kind,
                        model_name=str(model_name) if model_name else None,
                        started_at=started_at,
                        ended_at=ended_at,
                        latency_ms=latency_ms,
                        input_tokens=int(in_tok),
                        output_tokens=0,
                        tokens_total=int(in_tok),
                        usage_source="estimated",
                        had_tool_calls=False,
                        tool_call_count=0,
                        tool_names=[],
                        error_text=str(normalized_exc),
                    )
                )

            raise normalized_exc

    def _emit_event(
        self,
        *,
        event_type: str,
        node_name: str | None = None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        status: str | None = None,
        payload_json: dict[str, Any] | None = None,
        payload_text: str | None = None,
    ) -> None:
        self._events.emit(
            event_type=event_type,
            node_name=node_name,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            status=status,
            payload_json=payload_json,
            payload_text=payload_text,
        )

    async def astream(
        self,
        payload: Any,
        stream_mode: Sequence[str] | str | None = None,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        async for item in self._agent_runner.astream(payload, stream_mode=stream_mode):
            yield item

    async def ainvoke(self, payload: Any) -> Any:
        final_output: Any = None
        async for mode, data in self.astream(payload, stream_mode=("values",)):
            if mode == "values" and isinstance(data, Mapping):
                final_output = data.get("output")
        return final_output

    def invoke(self, payload: Any) -> Any:
        return self._run_async_in_thread(self.ainvoke(payload))

    def stream(
        self,
        payload: Any,
        stream_mode: Sequence[str] | str | None = None,
    ):
        q: Queue[Any] = Queue()
        sentinel = object()

        async def _producer() -> None:
            try:
                async for item in self.astream(payload, stream_mode=stream_mode):
                    q.put(("item", item))
            except Exception as exc:
                q.put(("error", exc))
            finally:
                q.put(("done", sentinel))

        def _runner() -> None:
            asyncio.run(_producer())

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()

        while True:
            kind, value = q.get()
            if kind == "item":
                yield value
            elif kind == "error":
                raise value
            else:
                break

    @staticmethod
    def _run_async_in_thread(coro: Any) -> Any:
        q: Queue[Any] = Queue()

        def _runner() -> None:
            try:
                result = asyncio.run(coro)
                q.put(("result", result))
            except Exception as exc:
                q.put(("error", exc))

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        kind, value = q.get()
        if kind == "error":
            raise value
        return value
