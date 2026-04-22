from __future__ import annotations

import json
import time
from typing import Any, AsyncGenerator, Mapping

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from .finalization_policy import FinalizationPolicy
from .runtime_config import RuntimeConfig
from .scratchpad import Scratchpad, ScratchpadConfig
from .runtime_types import (
    BoundModel,
    BuildAIMessageWithToolCalls,
    CurrentTelemetryContext,
    EmitEvent,
    InvokeWithTelemetry,
    JSONFromText,
    LimitToolCalls,
    ParsedToPayloadJSON,
    PayloadToHumanContent,
    RenderSystemPrompt,
    StreamModesInput,
    ValuesStateBuilder,
)
from .tool_executor import ToolExecutor


class AgentRunner:
    """Async runtime loop orchestrator for the hand-rolled SSE agent."""

    def __init__(
        self,
        *,
        bound_model: BoundModel,
        runtime_config: RuntimeConfig,
        run_timeout_s: float | None,
        agent_node_name: str,
        tools_node_name: str,
        finalization_policy: FinalizationPolicy,
        tool_executor: ToolExecutor,
        current_telemetry_context: CurrentTelemetryContext,
        render_system_prompt: RenderSystemPrompt,
        payload_to_human_content: PayloadToHumanContent,
        ainvoke_with_telemetry: InvokeWithTelemetry,
        ai_message_with_tool_calls: BuildAIMessageWithToolCalls,
        limit_tool_calls: LimitToolCalls,
        json_from_text: JSONFromText,
        parsed_to_payload_json: ParsedToPayloadJSON,
        emit_event: EmitEvent,
        values_state: ValuesStateBuilder,
    ) -> None:
        self.bound_model = bound_model
        self.runtime_config = runtime_config
        self.run_timeout_s = run_timeout_s
        self.agent_node_name = agent_node_name
        self.tools_node_name = tools_node_name
        self.finalization_policy = finalization_policy
        self.tool_executor = tool_executor
        self.current_telemetry_context = current_telemetry_context
        self.render_system_prompt = render_system_prompt
        self.payload_to_human_content = payload_to_human_content
        self.ainvoke_with_telemetry = ainvoke_with_telemetry
        self.ai_message_with_tool_calls = ai_message_with_tool_calls
        self.limit_tool_calls = limit_tool_calls
        self.json_from_text = json_from_text
        self.parsed_to_payload_json = parsed_to_payload_json
        self.emit_event = emit_event
        self.values_state = values_state

    @staticmethod
    def _resolve_modes(stream_mode: StreamModesInput) -> tuple[str, ...]:
        return (stream_mode,) if isinstance(stream_mode, str) else tuple(stream_mode or ("updates", "values"))

    def _remaining_timeout_s(self, *, run_started_t: float) -> float | None:
        if self.run_timeout_s is None:
            return None
        remaining = self.run_timeout_s - (time.perf_counter() - run_started_t)
        if remaining <= 0:
            raise TimeoutError("run_timeout_exceeded")
        return remaining

    def _build_call_messages(
        self,
        *,
        human_msg: HumanMessage,
        scratchpad: Scratchpad,
        retry_feedback: HumanMessage | None = None,
    ) -> list[BaseMessage]:
        call_messages: list[BaseMessage] = [SystemMessage(content=self.render_system_prompt()), human_msg]
        call_messages.extend(scratchpad.messages())
        if retry_feedback is not None:
            call_messages.append(retry_feedback)
        return call_messages

    @staticmethod
    def _short_excerpt(text: str, *, max_chars: int = 400) -> str:
        value = str(text or "").strip()
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + "...(truncated)"

    def _build_malformed_tool_retry_feedback(self, ai_msg: AIMessage) -> HumanMessage:
        excerpt = self._short_excerpt(str(getattr(ai_msg, "content", "") or ""))
        content = (
            "MALFORMED TOOL CALL DETECTED.\n"
            "Your previous response was not valid for the tool-calling contract.\n"
            "Return EXACTLY one JSON object and no extra text.\n"
            'Required format: {"tool_calls":[{"id":"call_<unique_id>","name":"<tool_name>","arguments":{...}}]}\n'
            "Rules:\n"
            "- Do not use markdown or code fences.\n"
            "- Do not add extra top-level keys.\n"
            "- Put all tool calls inside the single tool_calls array.\n"
            "- Use valid JSON only.\n"
            f"Previous malformed output excerpt:\n{excerpt}"
        )
        return HumanMessage(content=content)

    def _extract_normalized_tool_calls(self, ai_msg: AIMessage) -> list[dict[str, Any]]:
        raw_tool_calls = list(getattr(ai_msg, "tool_calls", []) or [])
        normalized_calls: list[dict[str, Any]] = []
        for item in raw_tool_calls:
            if not isinstance(item, Mapping):
                continue
            name = item.get("name")
            call_id = item.get("id")
            args = item.get("args", {})
            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(call_id, str) or not call_id.strip():
                continue
            if not isinstance(args, Mapping):
                args = {}
            normalized = {"id": call_id, "name": name.strip(), "args": dict(args)}
            if normalized:
                normalized_calls.append(normalized)
        return normalized_calls

    def _apply_tool_call_limit(
        self,
        *,
        ai_msg: AIMessage,
        tool_calls: list[dict[str, Any]],
    ) -> tuple[AIMessage, list[dict[str, Any]]]:
        limited_tool_calls, dropped_tool_calls = self.limit_tool_calls(tool_calls)
        if not (dropped_tool_calls and self.runtime_config.drop_extra_tool_calls):
            return ai_msg, tool_calls

        limited_ai_msg = self.ai_message_with_tool_calls(
            ai_msg,
            limited_tool_calls,
            extra_additional_kwargs={
                "dropped_tool_calls": [{"id": tc.get("id"), "name": tc.get("name")} for tc in dropped_tool_calls],
                "dropped_tool_call_count": len(dropped_tool_calls),
            },
        )
        return limited_ai_msg, limited_tool_calls

    def _emit_assistant_event_from_text(self, content: str) -> None:
        stripped = str(content or "").strip()
        if not stripped:
            return
        parsed, raw = self.json_from_text(stripped)
        self.emit_event(
            event_type="assistant",
            node_name=self.agent_node_name,
            payload_json=self.parsed_to_payload_json(parsed),
            payload_text=raw if parsed is None else None,
        )

    def _emit_tool_call_events(self, tool_calls: list[dict[str, Any]]) -> None:
        for tool_call in tool_calls:
            self.emit_event(
                event_type="tool_call",
                node_name=self.agent_node_name,
                tool_name=str(tool_call.get("name") or ""),
                tool_call_id=(str(tool_call.get("id")) if tool_call.get("id") is not None else None),
                payload_json={"args": tool_call.get("args")},
            )

    def _emit_tool_result_event(self, tool_message: ToolMessage) -> None:
        content = str(getattr(tool_message, "content", "") or "").strip()
        parsed, raw = self.json_from_text(content)
        self.emit_event(
            event_type="tool_result",
            node_name=self.tools_node_name,
            tool_name=getattr(tool_message, "name", None),
            tool_call_id=getattr(tool_message, "tool_call_id", None),
            status=getattr(tool_message, "status", None),
            payload_json={"result": parsed} if parsed is not None else None,
            payload_text=raw if parsed is None else None,
        )

    @staticmethod
    def _should_emit(modes: tuple[str, ...], mode: str) -> bool:
        return mode in modes

    async def astream(
        self,
        payload: Any,
        stream_mode: StreamModesInput = None,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        modes = self._resolve_modes(stream_mode)

        human_msg = HumanMessage(content=self.payload_to_human_content(payload))
        scratchpad = Scratchpad(
            config=ScratchpadConfig(
                include_final_assistant_output=self.runtime_config.scratchpad_include_final_assistant_output,
                include_raw_provider_debug=self.runtime_config.scratchpad_include_raw_provider_debug,
                verbose=self.runtime_config.scratchpad_verbose,
                log_token_estimates=self.runtime_config.scratchpad_log_token_estimates,
            )
        )
        streamed_messages: list[BaseMessage] = []

        final_output: Any = None
        done = False
        iteration = 0
        malformed_tool_retry_count = 0
        pending_retry_feedback: HumanMessage | None = None
        run_started_t = time.perf_counter()

        while not done:
            iteration += 1

            call_messages = self._build_call_messages(
                human_msg=human_msg,
                scratchpad=scratchpad,
                retry_feedback=pending_retry_feedback,
            )
            pending_retry_feedback = None

            ai_msg = await self.ainvoke_with_telemetry(
                call_kind="main_loop",
                iteration=iteration,
                messages=call_messages,
                invoke_fn=lambda: self.bound_model.ainvoke(call_messages),
                timeout_s=self._remaining_timeout_s(run_started_t=run_started_t),
            )

            tool_calls = self._extract_normalized_tool_calls(ai_msg)
            if tool_calls and str(ai_msg.content or "").strip():
                ai_msg = self.ai_message_with_tool_calls(
                    ai_msg,
                    tool_calls,
                    extra_additional_kwargs={"raw_tool_text": str(ai_msg.content or "")},
                )
            ai_msg, tool_calls = self._apply_tool_call_limit(ai_msg=ai_msg, tool_calls=tool_calls)

            streamed_messages.append(ai_msg)
            if tool_calls:
                scratchpad.append_assistant_tool_call(ai_msg)
            self._emit_tool_call_events(tool_calls)

            if self._should_emit(modes, "updates"):
                yield "updates", {self.agent_node_name: {"messages": [ai_msg]}}
            if self._should_emit(modes, "values"):
                yield "values", self.values_state(streamed_messages, iteration, False, None)

            if not tool_calls:
                malformed_detected = bool(
                    (getattr(ai_msg, "additional_kwargs", {}) or {}).get("malformed_tool_call_detected")
                )
                if (
                    malformed_detected
                    and self.runtime_config.malformed_tool_retry_enabled
                    and malformed_tool_retry_count < self.runtime_config.max_malformed_tool_retries
                ):
                    malformed_tool_retry_count += 1
                    pending_retry_feedback = self._build_malformed_tool_retry_feedback(ai_msg)
                    self.emit_event(
                        event_type="runtime_decision",
                        node_name=self.agent_node_name,
                        payload_json={
                            "decision": "retry_after_malformed_tool_call",
                            "retry_index": malformed_tool_retry_count,
                            "max_retries": self.runtime_config.max_malformed_tool_retries,
                        },
                    )
                    if self._should_emit(modes, "values"):
                        yield "values", self.values_state(streamed_messages, iteration, False, None)
                    continue

                self._emit_assistant_event_from_text(str(ai_msg.content or ""))
                scratchpad.append_final_assistant(ai_msg)

                decision = self.finalization_policy.maybe_finalize_from_assistant_no_tools(ai_msg)
                if decision.finalized:
                    final_output = decision.output
                else:
                    invalid = self.finalization_policy.finalize_invalid_output(
                        reason=decision.reason,
                        raw_output=str(ai_msg.content or ""),
                    )
                    final_output = invalid.output

                done = True
                break

            tool_msgs_by_index: dict[int, ToolMessage] = {}

            try:
                remaining = self._remaining_timeout_s(run_started_t=run_started_t)
                run_id, agent_name = self.current_telemetry_context()
                async for idx, tm in self.tool_executor.execute_tool_calls_batched(
                    tool_calls,
                    iteration=iteration,
                    run_id=run_id,
                    agent_name=agent_name,
                    timeout_s=remaining,
                ):
                    tool_msgs_by_index[idx] = tm
                    streamed_messages.append(tm)
                    self._emit_tool_result_event(tm)

                    if self._should_emit(modes, "updates"):
                        yield "updates", {self.tools_node_name: {"messages": [tm]}}
                    if self._should_emit(modes, "values"):
                        yield "values", self.values_state(streamed_messages, iteration, False, None)
            except TimeoutError:
                raise TimeoutError("run_timeout_exceeded")

            tool_msgs = [tool_msgs_by_index[idx] for idx in range(len(tool_calls)) if idx in tool_msgs_by_index]
            for tm in tool_msgs:
                scratchpad.append_tool_result(tm)

            for tc, tm in zip(tool_calls, tool_msgs):
                decision = self.finalization_policy.maybe_finalize_from_tool_result(tc, tm)
                if not decision.finalized:
                    if decision.reason == "schema_validation_error":
                        invalid = self.finalization_policy.finalize_invalid_output(
                            reason=decision.reason,
                            raw_output=str(getattr(tm, "content", "") or ""),
                        )
                        final_output = invalid.output
                        final_msg = AIMessage(
                            content=invalid.output_text or json.dumps(final_output, ensure_ascii=False)
                        )
                        streamed_messages.append(final_msg)
                        scratchpad.append_final_assistant(final_msg)
                        self._emit_assistant_event_from_text(str(final_msg.content or ""))
                        if self._should_emit(modes, "updates"):
                            yield "updates", {self.agent_node_name: {"messages": [final_msg]}}
                        done = True
                        break
                    continue

                final_output = decision.output
                final_text = decision.output_text or json.dumps(final_output, ensure_ascii=False)
                final_msg = AIMessage(content=final_text)
                streamed_messages.append(final_msg)
                scratchpad.append_final_assistant(final_msg)
                self._emit_assistant_event_from_text(final_text)
                if self._should_emit(modes, "updates"):
                    yield "updates", {self.agent_node_name: {"messages": [final_msg]}}
                done = True
                break

        if final_output is None:
            fallback = self.finalization_policy.finalize_no_output()
            final_output = fallback.output
            final_msg = AIMessage(content=fallback.output_text or json.dumps(final_output, ensure_ascii=False))
            streamed_messages.append(final_msg)
            scratchpad.append_final_assistant(final_msg)
            self._emit_assistant_event_from_text(str(final_msg.content or ""))
            if self._should_emit(modes, "updates"):
                yield "updates", {self.agent_node_name: {"messages": [final_msg]}}

        if self._should_emit(modes, "values"):
            yield "values", self.values_state(streamed_messages, iteration, True, final_output)
