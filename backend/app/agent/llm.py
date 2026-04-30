from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.agent.state import ChatHistoryMessage

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
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is required for LangChain Groq orchestration.")

    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    return ChatGroq(
        model=model,
        api_key=api_key,
        temperature=temperature,
    )


async def generate_response_text(
    *,
    system_prompt: str,
    history: list[ChatHistoryMessage],
) -> str:
    fallback_text = "Sorry, I ran into an issue while generating the response."
    timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "35"))

    async def _run_generation() -> str:
        model = get_chat_model()
        logger.info("[LangChainLLM] Calling Groq model=%s", model.model_name)

        messages = _to_langchain_messages(system_prompt=system_prompt, history=history)
        # Final-response mode: one LLM call per user turn.
        response = await model.ainvoke(messages)
        return _content_to_text(getattr(response, "content", "")).strip()

    try:
        final_text = await asyncio.wait_for(_run_generation(), timeout=timeout_seconds)
        return final_text or fallback_text
    except asyncio.TimeoutError:
        logger.exception("[LangChainLLM] LLM call timed out timeout_seconds=%s", timeout_seconds)
    except Exception:
        logger.exception("[LangChainLLM] LLM call failed")
    return fallback_text
