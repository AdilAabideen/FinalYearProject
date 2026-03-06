from __future__ import annotations
import inspect
from functools import lru_cache
from app.config import settings


@lru_cache
def get_chat_model():
    """
    Lazily construct and cache the chat model.

    Keeps imports optional so the rest of the API can run without LangChain deps
    installed until you actually start using agentic features.
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to `.env` (see `.env.example`)."
        )

    try:
        from langchain_openai import ChatOpenAI  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Missing dependency `langchain-openai`. Install it to use the agentic stack."
        ) from e

    kwargs = {"model": settings.OPENAI_MODEL}
    parameters = inspect.signature(ChatOpenAI).parameters
    if "api_key" in parameters:
        kwargs["api_key"] = settings.OPENAI_API_KEY
    elif "openai_api_key" in parameters:
        kwargs["openai_api_key"] = settings.OPENAI_API_KEY

    return ChatOpenAI(**kwargs)
