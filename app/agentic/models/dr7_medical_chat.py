from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Optional, Sequence, Union

import httpx
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ConfigDict, Field

from app.agentic.protocols import AllowedToolNames, build_tool_instruction


class Dr7MedicalChatModel(BaseChatModel):
    """
    Minimal LangChain ChatModel wrapper around Dr7's medical chat completions endpoint.

    Notes:
    - v1 only supports non-streaming responses (`stream=false`).
    - Dr7-native function calling is not available; `bind_tools()` is emulated
      through a JSON tool-call contract so LangGraph agents can run tool loops.
    """

    model_config = ConfigDict(frozen=True)

    model: str = Field(description="Dr7 model id (e.g. 'medgemma-4b-it').")
    base_url: str = Field(description="Base URL, e.g. 'https://dr7.ai/api/v1/medical'.")
    api_key: str = Field(description="Dr7 API key (Bearer token).", repr=False)

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout_s: float = 60.0

    def _llm_type(self) -> str:
        return "dr7-medical-chat"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model": self.model, "base_url": self.base_url}

    def _normalize_tool_calls(
        self,
        raw_tool_calls: Any,
        *,
        allowed_tool_names: AllowedToolNames = None,
    ) -> list[dict[str, Any]]:
        # TODO(protocol-types): migrate return type to list[NormalizedToolCall].
        if not isinstance(raw_tool_calls, list):
            return []

        normalized: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for raw_call in raw_tool_calls:
            if not isinstance(raw_call, dict):
                continue

            raw_function = raw_call.get("function")
            if isinstance(raw_function, dict):
                name = raw_function.get("name")
                raw_args = raw_function.get("arguments", {})
            else:
                name = raw_call.get("name")
                raw_args = raw_call.get("arguments", raw_call.get("args", {}))

            if not isinstance(name, str) or not name.strip():
                continue
            name = name.strip()

            if allowed_tool_names is not None and name not in allowed_tool_names:
                continue

            args: dict[str, Any]
            if isinstance(raw_args, str):
                try:
                    parsed_args = json.loads(raw_args)
                    args = parsed_args if isinstance(parsed_args, dict) else {"input": parsed_args}
                except Exception:
                    args = {"input": raw_args}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}

            call_id = raw_call.get("id")
            if not isinstance(call_id, str) or not call_id.strip():
                call_id = f"call_{uuid.uuid4().hex[:12]}"
            if call_id in seen_ids:
                call_id = f"call_{uuid.uuid4().hex[:12]}"
            seen_ids.add(call_id)

            normalized.append(
                {
                    "id": call_id,
                    "name": name,
                    "args": args,
                    "type": "tool_call",
                }
            )

        return normalized

    def _extract_tool_calls_from_text(
        self,
        content: str,
        *,
        allowed_tool_names: AllowedToolNames = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        # TODO(protocol-types): return ToolCallParseResult once parser modules are extracted.
        stripped = (content or "").strip()
        if not stripped:
            return [], False

        candidates = [stripped]
        if stripped.startswith("```") and stripped.endswith("```"):
            block = stripped[3:-3].strip()
            if block.lower().startswith("json"):
                block = block[4:].strip()
            candidates.append(block)

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except Exception:
                # Try JSONL (one JSON object per line) as a fallback.
                tool_calls: list[dict[str, Any]] = []
                all_lines_parsed = True
                for ln in candidate.splitlines():
                    line = ln.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        all_lines_parsed = False
                        continue

                    raw_calls: Any = []
                    if isinstance(obj, dict) and isinstance(obj.get("tool_calls"), list):
                        raw_calls = obj["tool_calls"]
                    elif isinstance(obj, dict) and isinstance(obj.get("name"), str):
                        raw_calls = [obj]
                    elif isinstance(obj, list):
                        raw_calls = obj

                    tool_calls.extend(
                        self._normalize_tool_calls(
                            raw_calls, allowed_tool_names=allowed_tool_names
                        )
                    )

                if tool_calls:
                    return tool_calls, all_lines_parsed
                continue

            raw_calls: Any = []
            if isinstance(parsed, dict) and isinstance(parsed.get("tool_calls"), list):
                raw_calls = parsed["tool_calls"]
            elif isinstance(parsed, dict) and isinstance(parsed.get("name"), str):
                raw_calls = [parsed]
            elif isinstance(parsed, list):
                raw_calls = parsed

            normalized = self._normalize_tool_calls(
                raw_calls, allowed_tool_names=allowed_tool_names
            )
            if normalized:
                return normalized, True

        return [], False

    def _to_dr7_messages(
        self,
        messages: Sequence[BaseMessage],
        *,
        allow_tool_messages: bool = False,
    ) -> list[dict[str, str]]:
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
                    raise ValueError(
                        "Dr7MedicalChatModel does not support tool calling (ToolMessage present)."
                    )
                role = "user"
            else:
                raise ValueError(f"Unsupported message type for Dr7: {type(msg).__name__}")

            if isinstance(msg, ToolMessage):
                tool_name = getattr(msg, "name", None) or "tool"
                tool_status = getattr(msg, "status", None) or "success"
                tool_id = getattr(msg, "tool_call_id", None) or "unknown"
                raw_content = (getattr(msg, "content", None) or "").strip()
                content = (
                    f"Tool result ({tool_name}, id={tool_id}, status={tool_status}):\n{raw_content}"
                )
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
                    if content:
                        content = f"{content}\n\n{rendered_calls}"
                    else:
                        content = rendered_calls
            out.append({"role": role, "content": content})
        return out

    def bind_tools(
        self,
        tools: Sequence[Union[dict[str, Any], type, Callable, BaseTool]],
        *,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """
        Bind tools for LangChain/LangGraph compatibility.

        Dr7 does not natively support function-calling in this wrapper; bound tool
        schemas are used to instruct the model to emit JSON tool calls that are then
        converted into `AIMessage.tool_calls`.
        """
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
        # LangGraph's `create_react_agent` binds tools with no tool_choice; for Dr7 we
        # default to requiring a tool call so it doesn't "answer in one go" without
        # producing `AIMessage.tool_calls`.
        if tool_choice is None:
            tool_choice = "any"
        return self.bind(
            tools=formatted_tools,
            tool_choice=tool_choice,
            **kwargs,
        )

    def _normalize_dr7_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """
        Normalize messages for strict llama chat templates.

        Rules:
        - Keep at most one leading system message (merge any additional system content into it).
        - Merge consecutive turns that share the same role.
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


    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        bound_tools = kwargs.get("tools")
        tool_choice = kwargs.get("tool_choice")
        tools: list[dict[str, Any]] = []
        if isinstance(bound_tools, list):
            tools = [t for t in bound_tools if isinstance(t, dict)]

        dr7_messages = self._to_dr7_messages(messages, allow_tool_messages=bool(tools))
        # if tools:
        #     dr7_messages = [
        #         {
        #             "role": "system",
        #             "content": self._tool_instruction(tools, tool_choice),
        #         },
        #         *dr7_messages,
        #     ]
        if tools:
            print(tools)
            tool_instruction = build_tool_instruction(
                tools,
                tool_choice,
                final_answer_tool_name="final_answer",
                highlight_final_answer=True,
            )
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
        dr7_messages = self._normalize_dr7_messages(dr7_messages)
        
        # print(json.dumps(dr7_messages))

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": dr7_messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if stop:
            payload["stop"] = stop

        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.post(url, headers=headers, json=payload)
        except Exception as e:
            raise RuntimeError(f"Dr7 request failed: {e}") from e

        if resp.status_code >= 400:
            detail = (resp.text or "").strip()
            if len(detail) > 5000:
                detail = detail[:5000] + "…(truncated)"
            raise RuntimeError(f"Dr7 API error {resp.status_code}: {detail}")

        try:
            data = resp.json()
        except Exception as e:
            text = (resp.text or "").strip()
            raise RuntimeError(f"Dr7 returned invalid JSON: {e}; body={text[:2000]}") from e

        try:
            choice_msg = data["choices"][0]["message"]
        except Exception as e:
            raise RuntimeError(f"Dr7 response missing choices/message/content: {data}") from e

        content = ""
        if isinstance(choice_msg, dict):
            content = (choice_msg.get("content") or "").strip()

        allowed_tool_names: AllowedToolNames = {
            t.get("function", {}).get("name")
            for t in tools
            if isinstance(t.get("function"), dict)
        }
        allowed_tool_names = {
            n for n in allowed_tool_names if isinstance(n, str) and n
        } or None

        tool_calls: list[dict[str, Any]] = []
        if tools and isinstance(choice_msg, dict):
            tool_calls = self._normalize_tool_calls(
                choice_msg.get("tool_calls"),
                allowed_tool_names=allowed_tool_names,
            )
            if not tool_calls:
                tool_calls, consumed_entire_text = self._extract_tool_calls_from_text(
                    content, allowed_tool_names=allowed_tool_names
                )
                if consumed_entire_text and tool_calls:
                    content = ""

        message = AIMessage(content=content, tool_calls=tool_calls)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation], llm_output={"raw": data})
