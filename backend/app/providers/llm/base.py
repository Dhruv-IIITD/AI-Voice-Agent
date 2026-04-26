from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any


Message = dict[str, Any]


@dataclass(frozen=True)
class ToolCallDirective:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ToolPlanningResult:
    tool_calls: list[ToolCallDirective]


class BaseLLMClient(ABC):
    """Deprecated compatibility interface (LangChain + LangGraph now own orchestration)."""

    @abstractmethod
    async def plan_tool_calls(
        self,
        *,
        system_prompt: str,
        history: Sequence[Message],
        tools: list[dict[str, Any]],
    ) -> ToolPlanningResult:
        raise NotImplementedError

    @abstractmethod
    async def stream_response(
        self,
        *,
        system_prompt: str,
        history: Sequence[Message],
    ) -> AsyncIterator[str]:
        raise NotImplementedError
