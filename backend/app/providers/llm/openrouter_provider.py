from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Sequence
from typing import Any

from openai import AsyncOpenAI

from app.providers.llm.base import BaseLLMClient, Message, ToolCallDirective, ToolPlanningResult

PLANNER_PROMPT = (
    "Decide whether tools are required before the assistant answers. "
    "If a tool is useful, call it. If no tool is needed, reply with NO_TOOL only."
)

logger = logging.getLogger(__name__)


class OpenRouterLLMClient(BaseLLMClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers=default_headers,
            timeout=30.0,
            max_retries=1,
        )
        self._model = model
        self._temperature = temperature

    async def plan_tool_calls(
        self,
        *,
        system_prompt: str,
        history: Sequence[Message],
        tools: list[dict[str, Any]],
    ) -> ToolPlanningResult:
        if not tools:
            return ToolPlanningResult(tool_calls=[])

        logger.info(
            "Starting OpenRouter tool planning request model=%s history_messages=%s tools=%s",
            self._model,
            len(history),
            len(tools),
        )
        started_at = time.perf_counter()

        try:
            async with asyncio.timeout(30):
                response = await self._client.chat.completions.create(
                    model=self._model,
                    temperature=0,
                    messages=[
                        {"role": "system", "content": PLANNER_PROMPT},
                        {"role": "system", "content": system_prompt},
                        *history,
                    ],
                    tools=tools,
                    tool_choice="auto",
                )
        except TimeoutError:
            logger.exception("OpenRouter tool planning timed out after 30 seconds")
            return ToolPlanningResult(tool_calls=[])
        except Exception:
            logger.exception("OpenRouter tool planning failed")
            return ToolPlanningResult(tool_calls=[])

        logger.info(
            "OpenRouter tool planning request finished duration_ms=%s",
            round((time.perf_counter() - started_at) * 1000, 2),
        )
        message = response.choices[0].message
        calls = []
        for call in message.tool_calls or []:
            calls.append(
                ToolCallDirective(
                    id=call.id or f"tool-{call.function.name}",
                    name=call.function.name,
                    arguments=call.function.arguments or "{}",
                )
            )
        return ToolPlanningResult(tool_calls=calls)

    async def stream_response(
        self,
        *,
        system_prompt: str,
        history: Sequence[Message],
    ) -> AsyncIterator[str]:
        logger.info(
            "Starting OpenRouter response stream model=%s history_messages=%s",
            self._model,
            len(history),
        )
        started_at = time.perf_counter()

        try:
            async with asyncio.timeout(45):
                stream = await self._client.chat.completions.create(
                    model=self._model,
                    temperature=self._temperature,
                    stream=True,
                    messages=[{"role": "system", "content": system_prompt}, *history],
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield delta
        except TimeoutError as exc:
            logger.exception("OpenRouter response stream timed out after 45 seconds")
            raise RuntimeError("OpenRouter response stream timed out.") from exc
        except Exception:
            logger.exception("OpenRouter response stream failed")
            raise
        finally:
            logger.info(
                "OpenRouter response stream finished duration_ms=%s",
                round((time.perf_counter() - started_at) * 1000, 2),
            )
