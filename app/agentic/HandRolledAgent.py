from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from datetime import datetime
from queue import Queue
from typing import Any, AsyncGenerator, Callable, Iterable, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool as lc_tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict

try:
    import tiktoken
except Exception:  # pragma: no cover - optional dependency at runtime
    tiktoken = None


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
    ) -> None:
        self.model = self._build_model(model=model, llm_kwargs=llm_kwargs)
        self.tools: list[BaseTool] = self._coerce_tools(tools or [])

        self.system_prompt = (
            system_prompt if isinstance(system_prompt, str) and system_prompt.strip() else "You are a helpful assistant."
        )
        self.response_format = response_format
        self.final_answer_tool_name = final_answer_tool_name

        # Ensure final_answer is available as an actual tool when structured output is requested.
        if self.final_answer_tool_name and self.response_format is not None:
            existing = {t.name for t in self.tools}
            if self.final_answer_tool_name not in existing:
                self.tools.append(self._build_final_answer_tool())

        self.tools_by_name: dict[str, BaseTool] = {t.name: t for t in self.tools}
        self.agent_node_name = agent_node_name
        self.tools_node_name = tools_node_name
        self.run_timeout_s = None if run_timeout_s is None else float(run_timeout_s)
        self._event_handlers: list[Callable[[dict[str, Any]], None]] = list(event_handlers or [])
        self._llm_call_handlers: list[Callable[[dict[str, Any]], None]] = list(llm_call_handlers or [])
        self._event_run_id: str | None = None
        self._event_agent_name: str | None = None
        self._event_seq: int = 0
        self._llm_call_index: int = 0

        if self.tools:
            self.bound_model = self.model.bind_tools(self.tools, tool_choice="any")
        else:
            self.bound_model = self.model

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
        for t in raw_tools:
            if isinstance(t, BaseTool):
                normalized.append(t)
            elif callable(t):
                normalized.append(lc_tool(t))
            else:
                raise TypeError(f"Unsupported tool type: {type(t)!r}")
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
        if self.response_format is None:
            return self.system_prompt

        if isinstance(self.response_format, dict):
            schema = self.response_format
        elif isinstance(self.response_format, type) and issubclass(self.response_format, BaseModel):
            schema = self.response_format.model_json_schema()
        else:
            schema = {"description": str(self.response_format)}

        return (
            f"{self.system_prompt}\n\n"
            "Return your final assistant output as strict JSON matching this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        )

    @staticmethod
    def _payload_to_human_content(payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("input"), str):
            return payload["input"]
        if isinstance(payload, dict) and isinstance(payload.get("messages"), list):
            for item in reversed(payload["messages"]):
                if isinstance(item, tuple) and len(item) == 2 and str(item[0]).lower() == "user":
                    return str(item[1])
                if isinstance(item, dict) and str(item.get("role", "")).lower() == "user":
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
    def _tool_output_to_text(value: Any) -> str:
        if isinstance(value, BaseModel):
            return value.model_dump_json()
        if isinstance(value, (dict, list, tuple, int, float, bool)) or value is None:
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def _normalize_final_output(value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        has_error = bool(normalized.get("error"))
        has_recommendation = isinstance(normalized.get("recommendation"), dict)
        if has_recommendation and not has_error:
            normalized["ok"] = True
        elif "ok" not in normalized and not has_error:
            normalized["ok"] = True
        return normalized

    @staticmethod
    def _structured_to_jsonable(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if hasattr(value, "model_dump") and callable(value.model_dump):
            try:
                return value.model_dump()
            except Exception:
                pass
        return value

    async def _generate_structured_response(
        self,
        messages: list[BaseMessage],
        *,
        timeout_s: float | None = None,
    ) -> Any | None:
        if self.response_format is None:
            return None
        try:
            structured_model = self.model.with_structured_output(self.response_format)
            response = await self._ainvoke_with_telemetry(
                call_kind="structured_output",
                messages=messages,
                invoke_fn=lambda: structured_model.ainvoke(messages),
                timeout_s=timeout_s,
            )
            return self._structured_to_jsonable(response)
        except TimeoutError:
            raise
        except Exception:
            return None

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
    def _normalize_tool_call(cls, obj: dict[str, Any]) -> dict[str, Any] | None:
        name = obj.get("name") or obj.get("tool_name")
        args = obj.get("args", obj.get("arguments", {}))
        call_id = obj.get("id") or obj.get("tool_call_id") or f"call_{uuid.uuid4().hex[:24]}"

        if not name and isinstance(obj.get("function"), dict):
            name = obj["function"].get("name")
            args = obj["function"].get("arguments", args)

        if not name:
            return None

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}

        if not isinstance(args, dict):
            args = {}

        return {"id": call_id, "name": name, "args": args}

    @classmethod
    def _recover_tool_calls_from_content(cls, content: str) -> list[dict[str, Any]]:
        recovered: list[dict[str, Any]] = []

        for obj in cls._iter_json_objects(content):
            if isinstance(obj, dict):
                tool_calls = obj.get("tool_calls")
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            norm = cls._normalize_tool_call(tc)
                            if norm:
                                recovered.append(norm)
                else:
                    norm = cls._normalize_tool_call(obj)
                    if norm:
                        recovered.append(norm)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        norm = cls._normalize_tool_call(item)
                        if norm:
                            recovered.append(norm)

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for tc in recovered:
            call_id = tc["id"]
            if call_id in seen:
                continue
            seen.add(call_id)
            deduped.append(tc)
        return deduped

    async def _execute_tool_call(self, tool_call: dict[str, Any]) -> ToolMessage:
        name = tool_call.get("name")
        call_id = tool_call.get("id") or f"call_{uuid.uuid4().hex[:24]}"
        args = tool_call.get("args") or {}

        if name not in self.tools_by_name:
            return ToolMessage(
                content=f"Unknown tool: {name}",
                tool_call_id=call_id,
                name=name,
                status="error",
            )

        tool_obj = self.tools_by_name[name]
        try:
            result = await tool_obj.ainvoke(args)
            return ToolMessage(
                content=self._tool_output_to_text(result),
                tool_call_id=call_id,
                name=name,
                artifact=result,
                status="success",
            )
        except Exception as exc:
            return ToolMessage(
                content=str(exc),
                tool_call_id=call_id,
                name=name,
                status="error",
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
        self._event_run_id = str(run_id)
        self._event_agent_name = str(agent_name)
        self._event_seq = int(start_seq)
        self._llm_call_index = 0

    def set_event_handlers(self, handlers: Sequence[Callable[[dict[str, Any]], None]] | None) -> None:
        self._event_handlers = list(handlers or [])

    def add_event_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        self._event_handlers.append(handler)

    def set_llm_call_handlers(self, handlers: Sequence[Callable[[dict[str, Any]], None]] | None) -> None:
        self._llm_call_handlers = list(handlers or [])

    def add_llm_call_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        self._llm_call_handlers.append(handler)

    @staticmethod
    def _parsed_to_payload_json(parsed: Any) -> dict[str, Any] | None:
        if parsed is None:
            return None
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}

    @staticmethod
    def _estimate_token_count(text: str) -> int:
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

    def _estimate_messages_tokens(self, messages: list[BaseMessage]) -> int:
        chunks: list[str] = []
        for msg in messages:
            role = type(msg).__name__
            content = getattr(msg, "content", "")
            chunks.append(f"{role}:{content}")
        return self._estimate_token_count("\n".join(chunks))

    @staticmethod
    def _usage_from_obj(obj: Any) -> tuple[int | None, int | None, int | None, str | None]:
        usage = getattr(obj, "usage_metadata", None)
        if isinstance(usage, dict):
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
        if isinstance(response_meta, dict):
            token_usage = response_meta.get("token_usage")
            if isinstance(token_usage, dict):
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

    def _emit_llm_call(
        self,
        *,
        call_kind: str,
        model_name: str | None,
        started_at: datetime,
        ended_at: datetime,
        latency_ms: int,
        input_tokens: int,
        output_tokens: int,
        tokens_total: int,
        usage_source: str,
        error_text: str | None = None,
    ) -> None:
        if not self._llm_call_handlers or self._event_run_id is None or self._event_agent_name is None:
            return

        self._llm_call_index += 1
        payload = {
            "run_id": self._event_run_id,
            "agent_name": self._event_agent_name,
            "call_index": self._llm_call_index,
            "model_name": model_name,
            "call_kind": call_kind,
            "started_at": started_at,
            "ended_at": ended_at,
            "latency_ms": latency_ms,
            "input_tokens": max(0, int(input_tokens)),
            "output_tokens": max(0, int(output_tokens)),
            "tokens_total": max(0, int(tokens_total)),
            "usage_source": usage_source,
            "error_text": error_text,
        }
        for handler in self._llm_call_handlers:
            handler(payload)

    async def _ainvoke_with_telemetry(
        self,
        *,
        call_kind: str,
        messages: list[BaseMessage],
        invoke_fn: Callable[[], Any],
        timeout_s: float | None = None,
    ) -> Any:
        started_at = datetime.utcnow()
        t0 = time.perf_counter()
        model_name = getattr(self.model, "model_name", None) or getattr(self.model, "model", None)

        try:
            if timeout_s is None:
                response = await invoke_fn()
            else:
                response = await asyncio.wait_for(invoke_fn(), timeout=timeout_s)
            ended_at = datetime.utcnow()
            latency_ms = int((time.perf_counter() - t0) * 1000)

            in_tok, out_tok, tot_tok, source = self._usage_from_obj(response)
            if in_tok is None or out_tok is None or tot_tok is None:
                if isinstance(response, AIMessage):
                    output_text = str(response.content or "")
                else:
                    output_text = self._tool_output_to_text(response)
                in_tok = self._estimate_messages_tokens(messages)
                out_tok = self._estimate_token_count(output_text)
                tot_tok = in_tok + out_tok
                source = "estimated"

            self._emit_llm_call(
                call_kind=call_kind,
                model_name=str(model_name) if model_name else None,
                started_at=started_at,
                ended_at=ended_at,
                latency_ms=latency_ms,
                input_tokens=in_tok,
                output_tokens=out_tok,
                tokens_total=tot_tok,
                usage_source=source or "estimated",
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
            in_tok = self._estimate_messages_tokens(messages)
            self._emit_llm_call(
                call_kind=call_kind,
                model_name=str(model_name) if model_name else None,
                started_at=started_at,
                ended_at=ended_at,
                latency_ms=latency_ms,
                input_tokens=in_tok,
                output_tokens=0,
                tokens_total=in_tok,
                usage_source="estimated",
                error_text=str(normalized_exc),
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
        if not self._event_handlers or self._event_run_id is None or self._event_agent_name is None:
            return

        self._event_seq += 1
        event = {
            "run_id": self._event_run_id,
            "agent_name": self._event_agent_name,
            "seq": self._event_seq,
            "event_type": event_type,
            "node_name": node_name,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "status": status,
            "payload_json": payload_json,
            "payload_text": payload_text,
        }
        for handler in self._event_handlers:
            handler(event)

    async def astream(
        self,
        payload: Any,
        stream_mode: Sequence[str] | str | None = None,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        modes = (
            (stream_mode,) if isinstance(stream_mode, str) else tuple(stream_mode or ("updates", "values"))
        )

        human_msg = HumanMessage(content=self._payload_to_human_content(payload))
        scratchpad: list[BaseMessage] = []
        streamed_messages: list[BaseMessage] = []

        final_output: Any = None
        done = False
        iteration = 0
        run_started_t = time.perf_counter()

        def _messages_for_finalization() -> list[BaseMessage]:
            msgs: list[BaseMessage] = [SystemMessage(content=self._render_system_prompt()), human_msg]
            msgs.extend(scratchpad)
            return msgs

        def _remaining_timeout_s() -> float | None:
            if self.run_timeout_s is None:
                return None
            remaining = self.run_timeout_s - (time.perf_counter() - run_started_t)
            if remaining <= 0:
                raise TimeoutError("run_timeout_exceeded")
            return remaining

        while not done:
            iteration += 1

            call_messages: list[BaseMessage] = [SystemMessage(content=self._render_system_prompt()), human_msg]
            call_messages.extend(scratchpad)

            ai_msg = await self._ainvoke_with_telemetry(
                call_kind="main_loop",
                messages=call_messages,
                invoke_fn=lambda: self.bound_model.ainvoke(call_messages),
                timeout_s=_remaining_timeout_s(),
            )
            tool_calls = list(getattr(ai_msg, "tool_calls", []) or [])

            if not tool_calls:
                recovered = self._recover_tool_calls_from_content(str(ai_msg.content or ""))
                if recovered:
                    ai_msg = AIMessage(
                        content="",
                        tool_calls=recovered,
                        additional_kwargs={
                            **getattr(ai_msg, "additional_kwargs", {}),
                            "raw_recovered_tool_text": str(ai_msg.content or ""),
                        },
                        response_metadata=getattr(ai_msg, "response_metadata", {}),
                        id=getattr(ai_msg, "id", None),
                        name=getattr(ai_msg, "name", None),
                    )
                    tool_calls = recovered
            elif str(ai_msg.content or "").strip():
                ai_msg = AIMessage(
                    content="",
                    tool_calls=tool_calls,
                    additional_kwargs={
                        **getattr(ai_msg, "additional_kwargs", {}),
                        "raw_tool_text": str(ai_msg.content or ""),
                    },
                    response_metadata=getattr(ai_msg, "response_metadata", {}),
                    id=getattr(ai_msg, "id", None),
                    name=getattr(ai_msg, "name", None),
                )

            streamed_messages.append(ai_msg)
            scratchpad.append(ai_msg)

            for tc in tool_calls:
                if not isinstance(tc, dict):
                    continue
                self._emit_event(
                    event_type="tool_call",
                    node_name=self.agent_node_name,
                    tool_name=tc.get("name"),
                    tool_call_id=tc.get("id"),
                    payload_json={"args": tc.get("args")},
                )

            if "updates" in modes:
                yield "updates", {self.agent_node_name: {"messages": [ai_msg]}}
            if "values" in modes:
                yield "values", self._values_state(streamed_messages, iteration, False, None)

            if not tool_calls:
                content = str(ai_msg.content or "").strip()
                if content:
                    parsed, raw = self._json_from_text(content)
                    self._emit_event(
                        event_type="assistant",
                        node_name=self.agent_node_name,
                        payload_json=self._parsed_to_payload_json(parsed),
                        payload_text=raw if parsed is None else None,
                    )
                structured = await self._generate_structured_response(
                    _messages_for_finalization(),
                    timeout_s=_remaining_timeout_s(),
                )
                if structured is not None:
                    final_output = self._normalize_final_output(structured)
                else:
                    parsed, raw = self._json_from_text(str(ai_msg.content or ""))
                    final_output = self._normalize_final_output(parsed if parsed is not None else raw)
                done = True
                break

            async def _execute_indexed_tool_call(idx: int, tc: dict[str, Any]) -> tuple[int, ToolMessage]:
                return idx, await self._execute_tool_call(tc)

            indexed_tasks = [
                asyncio.create_task(_execute_indexed_tool_call(idx, tc))
                for idx, tc in enumerate(tool_calls)
            ]
            tool_msgs_by_index: dict[int, ToolMessage] = {}

            try:
                remaining = _remaining_timeout_s()
                iterator = (
                    asyncio.as_completed(indexed_tasks)
                    if remaining is None
                    else asyncio.as_completed(indexed_tasks, timeout=remaining)
                )
                for task in iterator:
                    idx, tm = await task
                    tool_msgs_by_index[idx] = tm
                    streamed_messages.append(tm)

                    content = str(getattr(tm, "content", "") or "").strip()
                    parsed, raw = self._json_from_text(content)
                    tool_name = getattr(tm, "name", None)
                    self._emit_event(
                        event_type="tool_result",
                        node_name=self.tools_node_name,
                        tool_name=tool_name,
                        tool_call_id=getattr(tm, "tool_call_id", None),
                        status=getattr(tm, "status", None),
                        payload_json={"result": parsed} if parsed is not None else None,
                        payload_text=raw if parsed is None else None,
                    )

                    if "updates" in modes:
                        yield "updates", {self.tools_node_name: {"messages": [tm]}}
                    if "values" in modes:
                        yield "values", self._values_state(streamed_messages, iteration, False, None)
            except TimeoutError:
                for task in indexed_tasks:
                    task.cancel()
                raise TimeoutError("run_timeout_exceeded")

            tool_msgs = [
                tool_msgs_by_index[idx]
                for idx in range(len(tool_calls))
                if idx in tool_msgs_by_index
            ]
            for tm in tool_msgs:
                scratchpad.append(tm)

            if self.final_answer_tool_name:
                for tc, tm in zip(tool_calls, tool_msgs):
                    if tc.get("name") != self.final_answer_tool_name:
                        continue
                    parsed, raw = self._json_from_text(str(tm.content or ""))
                    final_output = self._normalize_final_output(parsed if parsed is not None else raw)
                    final_text = (
                        json.dumps(final_output, ensure_ascii=False)
                        if not isinstance(final_output, str)
                        else final_output
                    )
                    final_msg = AIMessage(content=final_text)
                    streamed_messages.append(final_msg)
                    final_parsed, final_raw = self._json_from_text(final_text)
                    self._emit_event(
                        event_type="assistant",
                        node_name=self.agent_node_name,
                        payload_json=self._parsed_to_payload_json(final_parsed),
                        payload_text=final_raw if final_parsed is None else None,
                    )
                    if "updates" in modes:
                        yield "updates", {self.agent_node_name: {"messages": [final_msg]}}
                    done = True
                    break

        if final_output is None:
            final_output = {"ok": False, "error": "no_output"}
            final_msg = AIMessage(content=json.dumps(final_output, ensure_ascii=False))
            streamed_messages.append(final_msg)
            final_parsed, final_raw = self._json_from_text(str(final_msg.content or ""))
            self._emit_event(
                event_type="assistant",
                node_name=self.agent_node_name,
                payload_json=self._parsed_to_payload_json(final_parsed),
                payload_text=final_raw if final_parsed is None else None,
            )
            if "updates" in modes:
                yield "updates", {self.agent_node_name: {"messages": [final_msg]}}

        if "values" in modes:
            yield "values", self._values_state(streamed_messages, iteration, True, final_output)

    async def ainvoke(self, payload: Any) -> Any:
        final_output: Any = None
        async for mode, data in self.astream(payload, stream_mode=("values",)):
            if mode == "values" and isinstance(data, dict):
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
