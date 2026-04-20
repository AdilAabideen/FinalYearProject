from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Literal, Optional, Sequence, Union

import httpx
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ConfigDict, Field

ESI1_ADAPTER_ID = 0
ESI2_ADAPTER_ID = 1
ESI345_ADAPTER_ID = 2
ES1_ADAPTER_ID = ESI1_ADAPTER_ID
ES2_ADAPTER_ID = ESI2_ADAPTER_ID
ES345_ADAPTER_ID = ESI345_ADAPTER_ID

ESIAdapterName = Literal["esi1", "esi2", "esi345"]

ESI_ADAPTER_ID_BY_NAME: dict[str, int] = {
    "esi1": ESI1_ADAPTER_ID,
    "esi2": ESI2_ADAPTER_ID,
    "esi345": ESI345_ADAPTER_ID,
}
SUPPORTED_ADAPTER_IDS = set(ESI_ADAPTER_ID_BY_NAME.values())

ESI_LORA_ADAPTERS: list[dict[str, Any]] = [
    {
        "id": ESI1_ADAPTER_ID,
        "path": "/Users/adil/Documents/University/MultiAgentResearch/UseCase1ESI/model_artifacts/adapters_gguf/esi1-lora.gguf",
        "scale": 1.0,
        "task_name": "",
        "prompt_prefix": "",
    },
    {
        "id": ESI2_ADAPTER_ID,
        "path": "/Users/adil/Documents/University/MultiAgentResearch/UseCase1ESI/model_artifacts/adapters_gguf/esi2-lora.gguf",
        "scale": 1.0,
        "task_name": "",
        "prompt_prefix": "",
    },
    {
        "id": ESI345_ADAPTER_ID,
        "path": "/Users/adil/Documents/University/MultiAgentResearch/UseCase1ESI/model_artifacts/adapters_gguf/esi345-lora.gguf",
        "scale": 1.0,
        "task_name": "",
        "prompt_prefix": "",
    },
]


class LlamaServerChat(BaseChatModel):
    """
    Minimal LangChain ChatModel wrapper around LLama Server chat completions endpoint.

    Notes:
    - v1 only supports non-streaming responses (`stream=false`).
    - Llama CPP function calling is not available; `bind_tools()` is emulated
      through a JSON tool-call contract so LangGraph agents can run tool loops.
    """

    model_config = ConfigDict(frozen=True)

    model: str = Field(description="Llama server model id (e.g. 'medgemma-4b-it').")
    base_url: str = Field(
        default="http://localhost:8080/v1",
        description="Base URL for llama-server OpenAI-compatible API.",
    )
    api_key: Optional[str] = Field(
        default="",
        description="Optional API key. Local llama-server usually does not require one.",
        repr=False,
    )
    adapter: Optional[ESIAdapterName] = Field(
        default=None,
        description="Default LoRA adapter literal: 'esi1' | 'esi2' | 'esi345'.",
    )
    adapter_id: Optional[int] = Field(
        default=None,
        description="Default LoRA adapter id. If omitted, inferred from model when possible.",
    )
    adapter_scale: float = Field(default=1.0, description="LoRA scale for selected adapter.")

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout_s: float = 60.0

    def _llm_type(self) -> str:
        return "llama-server-chat"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "base_url": self.base_url,
            "adapter": self.adapter,
            "adapter_id": self.adapter_id,
        }

    def _tool_instruction(
        self,
        tools: Sequence[dict[str, Any]],
        tool_choice: Optional[str],
    ) -> str:
        prompt_tools: list[dict[str, Any]] = []
        for tool in tools:
            fn = tool.get("function", {})
            if not isinstance(fn, dict):
                continue
            name = fn.get("name")
            if not isinstance(name, str) or not name:
                continue
            prompt_tools.append(
                {
                    "name": name,
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {}),
                }
            )

        parts = [
            "<tool_rules>"
            " - When tools are available, you MUST follow this tool-calling contract.",
            " - Return a SINGLE JSON object (no markdown, no extra text).",
            " - Tool-call format (exact):",
            ' - {"tool_calls":[{"id":"call_<unique_id>","name":"<tool_name>","arguments":{...}}]}',
            " - Do NOT output multiple JSON objects. If you need multiple tool calls, put them in the single tool_calls array.",
            " - When you are ready to finalize, call the final_answer tool with the full final payload.",
            " - Tool call ids must be unique per call.",
        ]

        if tool_choice == "any":
            parts.append("You must call at least one tool (tool call is required).")
        elif tool_choice and tool_choice not in {"auto", "none"}:
            parts.append(f'You must call the tool "{tool_choice}".')
        else:
            parts.append("If no tool is needed, respond with normal assistant text (not JSON).")
        
        parts.append(
            "</tool_rules> \n"
            "<available_tools>",
        )

        for tool in prompt_tools:
            name = str(tool.get("name", ""))
            desc = str(tool.get("description", ""))
            parameters = tool.get("parameters", {}) if isinstance(tool.get("parameters"), dict) else {}
            properties = parameters.get("properties", {})
            required = parameters.get("required", [])

            header = (
                "FINAL ANSWER TOOL -- CALL THIS WHEN YOU WANT TO OUTPUT THE FINAL ANSWER"
                if name == "final_answer"
                else "TOOL"
            )

            parts.append(
                "\n".join(
                    [
                        "",
                        f"[{header}]",
                        f"TOOL NAME: {name}",
                        f"TOOL DESCRIPTION: {desc}",
                        f"TOOL PARAMETERS (arguments schema): {json.dumps(properties, ensure_ascii=False)}",
                        f"TOOL REQUIRED PARAMETERS: {json.dumps(required, ensure_ascii=False)}",
                    ]
                )
            )

        parts.append("</available_tools>")
        return "\n".join(parts)


    def _normalize_tool_calls(
        self,
        raw_tool_calls: Any,
        *,
        allowed_tool_names: Optional[set[str]] = None,
    ) -> list[dict[str, Any]]:
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
        allowed_tool_names: Optional[set[str]] = None,
    ) -> tuple[list[dict[str, Any]], bool]:
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

    def _to_llama_messages(
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
                        "LlamaServerChat does not support tool calling (ToolMessage present)."
                    )
                role = "user"
            else:
                raise ValueError(f"Unsupported message type for Llama Server: {type(msg).__name__}")

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

    def _normalize_llama_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
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

    def _resolve_adapter_id(self, **kwargs: Any) -> Optional[int]:
        raw_adapter_id = kwargs.get("adapter_id", self.adapter_id)
        if raw_adapter_id is not None:
            adapter_id = int(raw_adapter_id)
            if adapter_id not in SUPPORTED_ADAPTER_IDS:
                supported = ", ".join(str(x) for x in sorted(SUPPORTED_ADAPTER_IDS))
                raise ValueError(
                    f"Unsupported adapter_id '{adapter_id}'. Expected one of: {supported}."
                )
            return adapter_id

        raw_adapter_name = kwargs.get("adapter", self.adapter)
        if isinstance(raw_adapter_name, str):
            adapter_name = raw_adapter_name.strip().lower()
            if adapter_name not in ESI_ADAPTER_ID_BY_NAME:
                supported = ", ".join(sorted(ESI_ADAPTER_ID_BY_NAME))
                raise ValueError(
                    f"Unsupported adapter '{raw_adapter_name}'. Expected one of: {supported}."
                )
            return ESI_ADAPTER_ID_BY_NAME[adapter_name]

        model_key = self.model.strip().lower()
        return ESI_ADAPTER_ID_BY_NAME.get(model_key)

    def bind_tools(
        self,
        tools: Sequence[Union[dict[str, Any], type, Callable, BaseTool]],
        *,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """
        Bind tools for LangChain/LangGraph compatibility.

        Llama Server does not natively support function-calling in this wrapper; bound
        tool schemas are used to instruct the model to emit JSON tool calls that are then
        converted into `AIMessage.tool_calls`.
        """
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
        # LangGraph's `create_react_agent` binds tools with no tool_choice; for this wrapper we
        # default to requiring a tool call so it doesn't "answer in one go" without
        # producing `AIMessage.tool_calls`.
        if tool_choice is None:
            tool_choice = "any"
        return self.bind(
            tools=formatted_tools,
            tool_choice=tool_choice,
            **kwargs,
        )

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

        llama_messages = self._to_llama_messages(messages, allow_tool_messages=bool(tools))
        if tools:
            # print(json.dumps(tools))
            tool_instruction = self._tool_instruction(tools, tool_choice)
            if llama_messages and llama_messages[0].get("role") == "system":
                existing = (llama_messages[0].get("content") or "").strip()
                if existing:
                    llama_messages[0]["content"] = f"{existing}\n\n{tool_instruction}"
                else:
                    llama_messages[0]["content"] = tool_instruction
            else:
                llama_messages = [
                    {"role": "system", "content": tool_instruction},
                    *llama_messages,
                ]
        llama_messages = self._normalize_llama_messages(llama_messages)

        print(json.dumps(llama_messages))

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": llama_messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if stop:
            payload["stop"] = stop
        adapter_id = self._resolve_adapter_id(**kwargs)
        adapter_scale = float(kwargs.get("adapter_scale", self.adapter_scale))
        # if adapter_id is not None:
        #     payload["lora"] = [{"id": int(adapter_id), "scale": adapter_scale}]

        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.post(url, headers=headers, json=payload)
        except Exception as e:
            raise RuntimeError(f"Llama Server request failed: {e}") from e

        if resp.status_code >= 400:
            detail = (resp.text or "").strip()
            if len(detail) > 5000:
                detail = detail[:5000] + "…(truncated)"
            raise RuntimeError(f"Llama Server API error {resp.status_code}: {detail}")

        try:
            data = resp.json()
        except Exception as e:
            text = (resp.text or "").strip()
            raise RuntimeError(f"Llama Server returned invalid JSON: {e}; body={text[:2000]}") from e

        try:
            choice_msg = data["choices"][0]["message"]
        except Exception as e:
            raise RuntimeError(
                f"Llama Server response missing choices/message/content: {data}"
            ) from e

        content = ""
        if isinstance(choice_msg, dict):
            content = (choice_msg.get("content") or "").strip()

        allowed_tool_names = {
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
