from __future__ import annotations
from contextlib import contextmanager
import threading
from typing import Any, Callable, Literal, Optional, Sequence, Union
import json

import httpx
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ConfigDict, Field

from app.agentic.protocols import (
    AllowedToolNames,
    coerce_bound_tools,
    extract_allowed_tool_names,
    inject_tool_instruction,
    normalize_chat_messages,
    to_provider_messages,
    normalize_tool_calls,
)

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


class _SerialRequestQueue:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._next_ticket = 0
        self._serving_ticket = 0

    @contextmanager
    def acquire(self):
        with self._condition:
            ticket = self._next_ticket
            self._next_ticket += 1
            while ticket != self._serving_ticket:
                self._condition.wait()

        try:
            yield
        finally:
            with self._condition:
                self._serving_ticket += 1
                self._condition.notify_all()


_SERIAL_QUEUE_GUARD = threading.Lock()
_SERIAL_QUEUES_BY_BASE_URL: dict[str, _SerialRequestQueue] = {}


def _queue_key_for(base_url: str) -> str:
    return str(base_url or "").rstrip("/")


def _serial_queue_for(base_url: str) -> _SerialRequestQueue:
    key = _queue_key_for(base_url)
    with _SERIAL_QUEUE_GUARD:
        queue = _SERIAL_QUEUES_BY_BASE_URL.get(key)
        if queue is None:
            queue = _SerialRequestQueue()
            _SERIAL_QUEUES_BY_BASE_URL[key] = queue
        return queue


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
        default="https://u31987bq9bfb30-8000.proxy.runpod.net/v1",
        # default="http://localhost:8080/v1",
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
    serialize_requests: bool = Field(
        default=False,
        description="When true, queue llama-server requests serially per backend URL.",
    )

    temperature: float = 0
    max_tokens: Optional[int] = 600
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

    def _normalize_llama_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """Normalize provider messages via shared protocol helper."""
        return normalize_chat_messages(messages)

    def _build_chat_completions_url(self) -> str:
        """Accept either a base API URL or a full chat completions endpoint."""
        normalized = self.base_url.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return normalized + "/chat/completions"

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

    def _apply_lora_payload(
        self,
        payload: dict[str, Any],
        *,
        adapter_id: Optional[int],
        adapter_scale: float,
    ) -> None:
        """Apply llama-only LoRA payload fields."""
        if adapter_id is None:
            return
        # Intentionally disabled to preserve existing transport behavior.
        payload["lora"] = [{"id": int(adapter_id), "scale": float(1.0)}]

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
        serialize_requests = bool(kwargs.get("serialize_requests", self.serialize_requests))
        if not serialize_requests:
            return self._generate_once(
                messages=messages,
                stop=stop,
                run_manager=run_manager,
                **kwargs,
            )

        with _serial_queue_for(self.base_url).acquire():
            return self._generate_once(
                messages=messages,
                stop=stop,
                run_manager=run_manager,
                **kwargs,
            )

    def _generate_once(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        bound_tools = kwargs.get("tools")
        tool_choice = kwargs.get("tool_choice")
        tools = coerce_bound_tools(bound_tools)

        llama_messages = to_provider_messages(
            messages,
            allow_tool_messages=bool(tools),
            tool_message_error="LlamaServerChat does not support tool calling (ToolMessage present).",
            unsupported_type_label="Llama Server",
        )
        llama_messages = inject_tool_instruction(
            llama_messages,
            tools=tools,
            tool_choice=tool_choice,
            final_answer_tool_name="final_answer",
            highlight_final_answer=True,
        )
        llama_messages = self._normalize_llama_messages(llama_messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": llama_messages,
            "temperature": 0,
            "top_k": 1,
            "top_p": 1,
            "seed": 42,
            "stream": False,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if stop:
            payload["stop"] = stop
        adapter_id = self._resolve_adapter_id(**kwargs)
        adapter_scale = float(kwargs.get("adapter_scale", self.adapter_scale))
        if adapter_id is not None and adapter_scale:
            self._apply_lora_payload(payload, adapter_id=adapter_id, adapter_scale=adapter_scale)

        url = self._build_chat_completions_url()
        headers = {"Content-Type": "application/json"}
        print(json.dumps(payload))
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

        allowed_tool_names: AllowedToolNames = extract_allowed_tool_names(tools)

        tool_calls: list[dict[str, Any]] = []
        if tools and isinstance(choice_msg, dict):
            tool_calls = normalize_tool_calls(
                choice_msg.get("tool_calls"),
                allowed_tool_names=allowed_tool_names,
            )

        message = AIMessage(content=content, tool_calls=tool_calls)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation], llm_output={"raw": data})
