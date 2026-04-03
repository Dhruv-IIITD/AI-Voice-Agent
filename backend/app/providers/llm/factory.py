from __future__ import annotations

from app.core.config import Settings
from app.providers.llm.base import BaseLLMClient
from app.providers.llm.openrouter_provider import OpenRouterLLMClient


def _is_openrouter_free_model(model: str) -> bool:
    normalized = model.strip().lower()
    return normalized == "openrouter/free" or normalized.endswith(":free")


def build_llm_client(settings: Settings) -> BaseLLMClient:
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is required for the OpenRouter LLM adapter.")
    if settings.openrouter_require_free and not _is_openrouter_free_model(settings.openrouter_model):
        raise ValueError(
            "OPENROUTER_MODEL must be a free OpenRouter model when OPENROUTER_REQUIRE_FREE=true. "
            "Use 'openrouter/free' or a model ending with ':free'."
        )

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
