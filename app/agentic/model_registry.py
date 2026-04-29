from __future__ import annotations

import inspect
from functools import lru_cache
from typing import Any, Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings


ModelProvider = Literal["openai", "dr7", "llama"]


class ModelPricing(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_per_1k: Optional[float] = None
    output_per_1k: Optional[float] = None
    unit: str = "per_1k_tokens"


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    provider: ModelProvider
    provider_model_id: Optional[str] = None
    description: Optional[str] = None
    context_length: Optional[int] = None
    max_tokens: Optional[int] = None
    pricing: Optional[ModelPricing] = None
    capabilities: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    supports_tools: bool = True
    default_temperature: float = 0.7


_MODEL_REGISTRY: dict[str, ModelSpec] = {
    # OpenAI (known defaults)
    "gpt-4o-mini": ModelSpec(
        id="gpt-4o-mini",
        provider="openai",
        description="OpenAI GPT-4o mini",
        supports_tools=True,
        default_temperature=0.7,
        pricing=ModelPricing(input_per_1k=0.001, output_per_1k=0.002),
    ),
    "medgemma-4b-it": ModelSpec(
        id="medgemma-4b-it",
        provider="dr7",
        description=(
            "MedGemma 4B Instruction Tuned - Optimized for medical text understanding and generation"
        ),
        context_length=8192,
        max_tokens=4096,
        pricing=ModelPricing(input_per_1k=0.00015, output_per_1k=0.00060),
        capabilities=[
            "medical_text_analysis",
            "symptom_analysis",
            "medical_qa",
            "clinical_reasoning",
        ],
        languages=["en", "zh"],
        supports_tools=True,
        default_temperature=0,
    ),
    "medgemma-4b-it-llama": ModelSpec(
        id="medgemma-4b-it-llama",
        provider="llama",
        provider_model_id="medgemma-4b-it",
        description=(
            "MedGemma 4B Instruction Tuned - Optimized for medical text understanding and generation Q_8 Quantization"
        ),
        context_length=8192,
        max_tokens=4096,
        pricing=ModelPricing(input_per_1k=0.00015, output_per_1k=0.00060),
        capabilities=[
            "medical_text_analysis",
            "symptom_analysis",
            "medical_qa",
            "clinical_reasoning",
        ],
        languages=["en", "zh"],
        supports_tools=True,
        default_temperature=0.7,
    ),
    "esi1": ModelSpec(
        id="esi1",
        provider="llama",
        description="Llama Server ESI-1 adapter profile.",
        supports_tools=True,
        default_temperature=0,
        pricing=ModelPricing(input_per_1k=0.00015, output_per_1k=0.00060),
        context_length=8192,
        max_tokens=4096,
    ),
    "esi2": ModelSpec(
        id="esi2",
        provider="llama",
        description="Llama Server ESI-2 adapter profile.",
        supports_tools=True,
        default_temperature=0,
        pricing=ModelPricing(input_per_1k=0.00015, output_per_1k=0.00060),
        context_length=8192,
        max_tokens=4096,
    ),
    "esi345": ModelSpec(
        id="esi345",
        provider="llama",
        description="Llama Server ESI-345 adapter profile.",
        supports_tools=True,
        default_temperature=0,
        pricing=ModelPricing(input_per_1k=0.00015, output_per_1k=0.00060),
        context_length=8192,
        max_tokens=4096,
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
        default_temperature=0.7,
    )


def validate_model_for_agent(
    *,
    model_id: str,
    agent_name: str,
    requires_tools: bool,
) -> ModelSpec:
    spec = resolve_model_spec(model_id)
    if requires_tools and not spec.supports_tools:
        raise ValueError(
            f"Model '{model_id}' does not support tool calling, but agent '{agent_name}' requires tools."
        )
    return spec


@lru_cache(maxsize=32)
def get_chat_model(model_id: str) -> BaseChatModel:
    spec = resolve_model_spec(model_id)
    if spec.provider == "openai":
        return _build_openai_chat_model(spec)
    if spec.provider == "dr7":
        return _build_dr7_chat_model(spec)
    if spec.provider == "llama":
        return build_llama_model(spec)
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
    if spec.provider != "dr7":
        raise RuntimeError(f"Cannot build Dr7 model for provider '{spec.provider}'.")
    if not settings.DR7_API_KEY:
        raise RuntimeError("DR7_API_KEY is not set. Add it to `.env` to use Dr7 models.")

    from app.agentic.models.dr7_medical_chat import Dr7MedicalChatModel

    return Dr7MedicalChatModel(
        model=spec.provider_model_id or spec.id,
        base_url=settings.DR7_MEDICAL_BASE_URL,
        api_key=settings.DR7_API_KEY,
        temperature=spec.default_temperature,
        max_tokens=spec.max_tokens,
        rate_limit_max_retries=settings.DR7_RATE_LIMIT_MAX_RETRIES,
        rate_limit_backoff_initial_s=settings.DR7_RATE_LIMIT_BACKOFF_INITIAL_S,
        rate_limit_backoff_multiplier=settings.DR7_RATE_LIMIT_BACKOFF_MULTIPLIER,
        rate_limit_backoff_max_s=settings.DR7_RATE_LIMIT_BACKOFF_MAX_S,
    )


def build_llama_model(spec: ModelSpec) -> BaseChatModel:
    if spec.provider != "llama":
        raise RuntimeError(f"Cannot build llama model for provider '{spec.provider}'.")
    from app.agentic.models.llama_server_chat import LlamaServerChat

    adapter_by_model_id: dict[str, str] = {
        "esi1": "esi1",
        "esi2": "esi2",
        "esi345": "esi345",
    }
    adapter = adapter_by_model_id.get(spec.id)

    return LlamaServerChat(
        model=spec.provider_model_id or spec.id,
        base_url=settings.LLAMA_SERVER_BASE_URL,
        api_key=settings.LLAMA_SERVER_API_KEY or "",
        adapter=adapter,
        temperature=spec.default_temperature,
        max_tokens=spec.max_tokens,
    )
