from __future__ import annotations

from app.core.config import Settings
from app.providers.llm.base import BaseLLMClient
from app.providers.llm.openai_provider import OpenAILLMClient
from app.providers.llm.openrouter_provider import OpenRouterLLMClient


def _is_openrouter_free_model(model: str) -> bool:
    normalized = model.strip().lower()
    return normalized == "openrouter/free" or normalized.endswith(":free")


def build_llm_client(settings: Settings) -> BaseLLMClient:
    provider = settings.llm_provider.lower()

    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouter.")
        if settings.openrouter_require_free and not _is_openrouter_free_model(settings.openrouter_model):
            raise ValueError("OPENROUTER_MODEL must be a free model when OPENROUTER_REQUIRE_FREE=true.")

        headers = {
            "HTTP-Referer": settings.openrouter_site_url or settings.frontend_origin,
            "X-Title": settings.openrouter_app_name or settings.app_name,
        }
        return OpenRouterLLMClient(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            temperature=settings.llm_temperature,
            default_headers=headers,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required.")
        return OpenAILLMClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=settings.llm_temperature,
        )

    if provider == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required.")
        return OpenAILLMClient(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=settings.llm_temperature,
            base_url="https://api.groq.com/openai/v1",
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required.")
        return OpenAILLMClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            temperature=settings.llm_temperature,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")
