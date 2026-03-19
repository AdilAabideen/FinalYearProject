from __future__ import annotations

import inspect
from functools import lru_cache
from typing import Any, Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings


ModelProvider = Literal["openai", "dr7"]


class ModelPricing(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_per_1k: Optional[float] = None
    output_per_1k: Optional[float] = None
    unit: str = "per_1k_tokens"


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    provider: ModelProvider
    description: Optional[str] = None
    context_length: Optional[int] = None
    max_tokens: Optional[int] = None
    pricing: Optional[ModelPricing] = None
    capabilities: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    supports_tools: bool = True
    supports_structured_output: bool = True
    default_temperature: float = 0.7


_MODEL_REGISTRY: dict[str, ModelSpec] = {
    # OpenAI (known defaults)
    "gpt-4o-mini": ModelSpec(
        id="gpt-4o-mini",
        provider="openai",
        description="OpenAI GPT-4o mini",
        supports_tools=True,
        supports_structured_output=True,
        default_temperature=0.7,
    ),
    # Dr7
    "medgemma-4b-it": ModelSpec(
        id="medgemma-4b-it",
        provider="dr7",
        description=(
            "MedGemma 4B Instruction Tuned - Optimized for medical text understanding and generation"
        ),
        context_length=8192,
        max_tokens=4096,
        pricing=ModelPricing(input_per_1k=0.001, output_per_1k=0.002),
        capabilities=[
            "medical_text_analysis",
            "symptom_analysis",
            "medical_qa",
            "clinical_reasoning",
        ],
        languages=["en", "zh"],
        supports_tools=True,
        supports_structured_output=True,
        default_temperature=0.7,
    ),
}


def list_registered_models() -> list[ModelSpec]:
    return sorted(_MODEL_REGISTRY.values(), key=lambda s: s.id)


def get_registered_model_spec(model_id: str) -> ModelSpec:
    return _MODEL_REGISTRY[model_id]


def resolve_model_spec(model_id: str) -> ModelSpec:
    """
    Resolve a model id to a spec.

    - If the model is registered, return the registered spec.
    - Otherwise, treat it as an OpenAI model id (no metadata).
    """
    spec = _MODEL_REGISTRY.get(model_id)
    if spec is not None:
        return spec

    return ModelSpec(
        id=model_id,
        provider="openai",
        description=None,
        supports_tools=True,
        supports_structured_output=True,
        default_temperature=0.7,
    )


def validate_model_for_agent(
    *,
    model_id: str,
    agent_name: str,
    requires_tools: bool,
    requires_structured_output: bool,
) -> ModelSpec:
    spec = resolve_model_spec(model_id)
    if requires_tools and not spec.supports_tools:
        raise ValueError(
            f"Model '{model_id}' does not support tool calling, but agent '{agent_name}' requires tools."
        )
    if requires_structured_output and not spec.supports_structured_output:
        raise ValueError(
            f"Model '{model_id}' does not support structured output, but agent '{agent_name}' requires it."
        )
    return spec


@lru_cache(maxsize=32)
def get_chat_model(model_id: str) -> BaseChatModel:
    spec = resolve_model_spec(model_id)
    if spec.provider == "openai":
        return _build_openai_chat_model(spec)
    if spec.provider == "dr7":
        return _build_dr7_chat_model(spec)
    raise RuntimeError(f"Unsupported model provider: {spec.provider}")


def _build_openai_chat_model(spec: ModelSpec) -> BaseChatModel:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to `.env` to use OpenAI models.")

    try:
        from langchain_openai import ChatOpenAI  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Missing dependency `langchain-openai`. Install it to use OpenAI models."
        ) from e

    kwargs: dict[str, Any] = {"model": spec.id, "temperature": spec.default_temperature}
    parameters = inspect.signature(ChatOpenAI).parameters
    if "api_key" in parameters:
        kwargs["api_key"] = settings.OPENAI_API_KEY
    elif "openai_api_key" in parameters:
        kwargs["openai_api_key"] = settings.OPENAI_API_KEY

    return ChatOpenAI(**kwargs)


def _build_dr7_chat_model(spec: ModelSpec) -> BaseChatModel:
    if not settings.DR7_API_KEY:
        raise RuntimeError("DR7_API_KEY is not set. Add it to `.env` to use Dr7 models.")

    from app.agentic.models.dr7_medical_chat import Dr7MedicalChatModel

    return Dr7MedicalChatModel(
        model=spec.id,
        base_url=settings.DR7_MEDICAL_BASE_URL,
        api_key=settings.DR7_API_KEY,
        temperature=spec.default_temperature,
        max_tokens=spec.max_tokens,
    )
