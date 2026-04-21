from __future__ import annotations

import json
import time
from typing import Any, AsyncGenerator, Callable, Mapping, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from .finalization_policy import FinalizationPolicy
from .runtime_config import RuntimeConfig
from .tool_executor import ToolExecutor


class AgentRunner:
    """Async runtime loop orchestrator for the hand-rolled SSE agent."""

    def __init__(
        self,
        *,
        bound_model: Any,
        runtime_config: RuntimeConfig,
        run_timeout_s: float | None,
        agent_node_name: str,
        tools_node_name: str,
        finalization_policy: FinalizationPolicy,
        tool_executor: ToolExecutor,
        current_telemetry_context: Callable[[], tuple[str | None, str | None]],
        render_system_prompt: Callable[[], str],
        payload_to_human_content: Callable[[Any], str],
        ainvoke_with_telemetry: Callable[..., Any],
        normalize_tool_call: Callable[[Mapping[str, Any]], dict[str, Any] | None],
        recover_tool_calls_from_content: Callable[[str], list[dict[str, Any]]],
        ai_message_with_tool_calls: Callable[..., AIMessage],
        limit_tool_calls: Callable[[list[dict[str, Any]]], tuple[list[dict[str, Any]], list[dict[str, Any]]]],
        json_from_text: Callable[[str], tuple[Any | None, str]],
        parsed_to_payload_json: Callable[[Any], dict[str, Any] | None],
        emit_event: Callable[..., None],
        values_state: Callable[[list[BaseMessage], int, bool, Any], dict[str, Any]],
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
        self.normalize_tool_call = normalize_tool_call
        self.recover_tool_calls_from_content = recover_tool_calls_from_content
        self.ai_message_with_tool_calls = ai_message_with_tool_calls
        self.limit_tool_calls = limit_tool_calls
        self.json_from_text = json_from_text
        self.parsed_to_payload_json = parsed_to_payload_json
        self.emit_event = emit_event
        self.values_state = values_state

    async def astream(
        self,
        payload: Any,
        stream_mode: Sequence[str] | str | None = None,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        modes = (
            (stream_mode,) if isinstance(stream_mode, str) else tuple(stream_mode or ("updates", "values"))
        )

        human_msg = HumanMessage(content=self.payload_to_human_content(payload))
        scratchpad: list[BaseMessage] = []
        streamed_messages: list[BaseMessage] = []

        final_output: Any = None
        done = False
        iteration = 0
        run_started_t = time.perf_counter()

        def _remaining_timeout_s() -> float | None:
            if self.run_timeout_s is None:
                return None
            remaining = self.run_timeout_s - (time.perf_counter() - run_started_t)
            if remaining <= 0:
                raise TimeoutError("run_timeout_exceeded")
            return remaining

        while not done:
            iteration += 1

            call_messages: list[BaseMessage] = [SystemMessage(content=self.render_system_prompt()), human_msg]
            call_messages.extend(scratchpad)

            ai_msg = await self.ainvoke_with_telemetry(
                call_kind="main_loop",
                iteration=iteration,
                messages=call_messages,
                invoke_fn=lambda: self.bound_model.ainvoke(call_messages),
                timeout_s=_remaining_timeout_s(),
            )

            raw_tool_calls = list(getattr(ai_msg, "tool_calls", []) or [])
            tool_calls: list[dict[str, Any]] = []
            for item in raw_tool_calls:
                if isinstance(item, Mapping):
                    normalized = self.normalize_tool_call(item)
                    if normalized:
                        tool_calls.append(normalized)

            if not tool_calls and self.runtime_config.allow_text_tool_recovery:
                recovered = self.recover_tool_calls_from_content(str(ai_msg.content or ""))
                if recovered:
                    ai_msg = self.ai_message_with_tool_calls(
                        ai_msg,
                        recovered,
                        extra_additional_kwargs={
                            "raw_recovered_tool_text": str(ai_msg.content or ""),
                        },
                    )
                    tool_calls = recovered
            elif str(ai_msg.content or "").strip():
                ai_msg = self.ai_message_with_tool_calls(
                    ai_msg,
                    tool_calls,
                    extra_additional_kwargs={
                        "raw_tool_text": str(ai_msg.content or ""),
                    },
                )

            limited_tool_calls, dropped_tool_calls = self.limit_tool_calls(tool_calls)
            if dropped_tool_calls and self.runtime_config.drop_extra_tool_calls:
                tool_calls = limited_tool_calls
                ai_msg = self.ai_message_with_tool_calls(
                    ai_msg,
                    tool_calls,
                    extra_additional_kwargs={
                        "dropped_tool_calls": [
                            {"id": tc.get("id"), "name": tc.get("name")} for tc in dropped_tool_calls
                        ],
                        "dropped_tool_call_count": len(dropped_tool_calls),
                    },
                )

            streamed_messages.append(ai_msg)
            scratchpad.append(ai_msg)

            for tc in tool_calls:
                self.emit_event(
                    event_type="tool_call",
                    node_name=self.agent_node_name,
                    tool_name=str(tc.get("name") or ""),
                    tool_call_id=(str(tc.get("id")) if tc.get("id") is not None else None),
                    payload_json={"args": tc.get("args")},
                )

            if "updates" in modes:
                yield "updates", {self.agent_node_name: {"messages": [ai_msg]}}
            if "values" in modes:
                yield "values", self.values_state(streamed_messages, iteration, False, None)

            if not tool_calls:
                content = str(ai_msg.content or "").strip()
                if content:
                    parsed, raw = self.json_from_text(content)
                    self.emit_event(
                        event_type="assistant",
                        node_name=self.agent_node_name,
                        payload_json=self.parsed_to_payload_json(parsed),
                        payload_text=raw if parsed is None else None,
                    )

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
                remaining = _remaining_timeout_s()
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

                    content = str(getattr(tm, "content", "") or "").strip()
                    parsed, raw = self.json_from_text(content)
                    tool_name = getattr(tm, "name", None)
                    self.emit_event(
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
                        yield "values", self.values_state(streamed_messages, iteration, False, None)
            except TimeoutError:
                raise TimeoutError("run_timeout_exceeded")

            tool_msgs = [tool_msgs_by_index[idx] for idx in range(len(tool_calls)) if idx in tool_msgs_by_index]
            for tm in tool_msgs:
                scratchpad.append(tm)

            for tc, tm in zip(tool_calls, tool_msgs):
                decision = self.finalization_policy.maybe_finalize_from_tool_result(tc, tm)
                if not decision.finalized:
                    continue

                final_output = decision.output
                final_text = decision.output_text or json.dumps(final_output, ensure_ascii=False)
                final_msg = AIMessage(content=final_text)
                streamed_messages.append(final_msg)
                final_parsed, final_raw = self.json_from_text(final_text)
                self.emit_event(
                    event_type="assistant",
                    node_name=self.agent_node_name,
                    payload_json=self.parsed_to_payload_json(final_parsed),
                    payload_text=final_raw if final_parsed is None else None,
                )
                if "updates" in modes:
                    yield "updates", {self.agent_node_name: {"messages": [final_msg]}}
                done = True
                break

        if final_output is None:
            fallback = self.finalization_policy.finalize_no_output()
            final_output = fallback.output
            final_msg = AIMessage(content=fallback.output_text or json.dumps(final_output, ensure_ascii=False))
            streamed_messages.append(final_msg)
            final_parsed, final_raw = self.json_from_text(str(final_msg.content or ""))
            self.emit_event(
                event_type="assistant",
                node_name=self.agent_node_name,
                payload_json=self.parsed_to_payload_json(final_parsed),
                payload_text=final_raw if final_parsed is None else None,
            )
            if "updates" in modes:
                yield "updates", {self.agent_node_name: {"messages": [final_msg]}}

        if "values" in modes:
            yield "values", self.values_state(streamed_messages, iteration, True, final_output)
