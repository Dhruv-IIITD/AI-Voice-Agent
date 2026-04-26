from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.state import ChatHistoryMessage, DeltaCallback

logger = logging.getLogger(__name__)


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                maybe_text = part.get("text")
                if isinstance(maybe_text, str):
                    text_parts.append(maybe_text)
            elif isinstance(part, str):
                text_parts.append(part)
        return "".join(text_parts)

    return ""


def _to_langchain_messages(
    *,
    system_prompt: str,
    history: list[ChatHistoryMessage],
) -> list[BaseMessage]:
    messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
    for message in history:
        role = str(message.get("role") or "")
        content = str(message.get("content") or "")
        if role == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required for LangChain OpenRouter orchestration.")

    model = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus:free")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    headers: dict[str, str] = {}
    site_url = os.getenv("OPENROUTER_SITE_URL")
    app_name = os.getenv("OPENROUTER_APP_NAME")
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_name:
        headers["X-Title"] = app_name

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
        streaming=True,
        default_headers=headers or None,
    )


async def generate_response_text(
    *,
    system_prompt: str,
    history: list[ChatHistoryMessage],
    on_delta: DeltaCallback | None = None,
) -> str:
    fallback_text = "Sorry, I had trouble generating that response. Please try again."
    timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "35"))

    async def _run_generation() -> str:
        model = get_chat_model()
        logger.info("[LangChainLLM] Calling OpenRouter model=%s", model.model_name)

        messages = _to_langchain_messages(system_prompt=system_prompt, history=history)
        full_response_parts: list[str] = []

        async for chunk in model.astream(messages):
            delta = _content_to_text(getattr(chunk, "content", ""))
            if not delta:
                continue
            full_response_parts.append(delta)
            if on_delta is not None:
                await on_delta(delta)

        final_text = "".join(full_response_parts).strip()
        if final_text:
            return final_text

        # Fallback to non-streaming invoke if provider returns an empty stream.
        response = await model.ainvoke(messages)
        final_text = _content_to_text(getattr(response, "content", "")).strip()
        if final_text and on_delta is not None:
            await on_delta(final_text)
        return final_text

    try:
        return await asyncio.wait_for(_run_generation(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.exception("[LangChainLLM] LLM call timed out timeout_seconds=%s", timeout_seconds)
    except Exception:
        logger.exception("[LangChainLLM] LLM call failed")

    if on_delta is not None:
        await on_delta(fallback_text)
    return fallback_text
