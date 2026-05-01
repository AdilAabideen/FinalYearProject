from __future__ import annotations

from typing import Any, Callable, Optional, Sequence, Union

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
    normalize_tool_calls,
    to_provider_messages,
)


class HuggingFaceRouterChatModel(BaseChatModel):
    """
    Minimal LangChain ChatModel wrapper for Hugging Face Router chat completions.

    Notes:
    - Uses the OpenAI-compatible HF Router endpoint.
    - Keeps this repo's existing tool-emulation contract so agent behavior stays
      consistent across providers, while still parsing native tool calls if
      the provider returns them.
    """

    model_config = ConfigDict(frozen=True)

    model: str = Field(description="HF Router model id, e.g. 'org/model:provider'.")
    base_url: str = Field(
        description="Base URL for HF Router OpenAI-compatible API, e.g. 'https://router.huggingface.co/v1'."
    )
    api_key: str = Field(
        description="Auth token for the upstream OpenAI-compatible endpoint.",
        repr=False,
    )

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout_s: float = 60.0

    def _llm_type(self) -> str:
        return "hf-router-chat"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model": self.model, "base_url": self.base_url}

    def bind_tools(
        self,
        tools: Sequence[Union[dict[str, Any], type, Callable, BaseTool]],
        *,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
        if tool_choice is None:
            tool_choice = "any"
        return self.bind(
            tools=formatted_tools,
            tool_choice=tool_choice,
            **kwargs,
        )

    def _normalize_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        return normalize_chat_messages(messages)

    def _build_chat_completions_url(self) -> str:
        normalized = self.base_url.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return normalized + "/chat/completions"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        bound_tools = kwargs.get("tools")
        tool_choice = kwargs.get("tool_choice")
        multi_agent = bool(kwargs.get("multi_agent"))
        handoff_names = list(kwargs.get("handoff_names") or [])
        tools = coerce_bound_tools(bound_tools)

        provider_messages = to_provider_messages(
            messages,
            allow_tool_messages=bool(tools),
            tool_message_error="HuggingFaceRouterChatModel does not support ToolMessage passthrough.",
            unsupported_type_label="HF Router",
        )
        provider_messages = inject_tool_instruction(
            provider_messages,
            tools=tools,
            tool_choice=tool_choice,
            multi_agent=multi_agent,
            handoff_names=handoff_names,
            final_answer_tool_name="final_answer",
            highlight_final_answer=not multi_agent,
        )
        provider_messages = self._normalize_messages(provider_messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": provider_messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if stop:
            payload["stop"] = stop

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.post(
                    self._build_chat_completions_url(),
                    headers=headers,
                    json=payload,
                )
        except Exception as e:
            raise RuntimeError(f"HF Router request failed: {e}") from e

        if resp.status_code >= 400:
            detail = (resp.text or "").strip()
            if len(detail) > 5000:
                detail = detail[:5000] + "…(truncated)"
            raise RuntimeError(f"HF Router API error {resp.status_code}: {detail}")

        try:
            data = resp.json()
        except Exception as e:
            text = (resp.text or "").strip()
            raise RuntimeError(f"HF Router returned invalid JSON: {e}; body={text[:2000]}") from e

        try:
            choice_msg = data["choices"][0]["message"]
        except Exception as e:
            raise RuntimeError(f"HF Router response missing choices/message/content: {data}") from e

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
