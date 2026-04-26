from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from app.agent.graph import AgentGraphResult, VoiceAgentGraph
from app.agent.memory import SessionMemory
from app.agents.catalog import AgentDefinition

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConversationEvent:
    kind: Literal["tool_call", "assistant_delta", "assistant_complete"]
    text: str = ""
    tool_name: str | None = None
    tool_arguments: dict[str, object] | None = None
    tool_result_summary: str | None = None
    retrieved_chunks: list[dict[str, object]] | None = None
    memory_summary: str | None = None


class ConversationSession:
    _max_history_messages = 14

    def __init__(
        self,
        *,
        agent: AgentDefinition,
    ) -> None:
        self._agent = agent
        self._memory = SessionMemory(session_id=f"{agent.id}-{uuid4().hex[:8]}")
        self._history: list[dict[str, object]] = []
        self._graph = VoiceAgentGraph(agent=agent)

    async def stream_reply(self, user_text: str) -> AsyncIterator[ConversationEvent]:
        logger.info("Conversation turn started agent=%s user_text=%s", self._agent.id, user_text)

        self._history.append({"role": "user", "content": user_text})
        self._history = self._history[-self._max_history_messages :]

        delta_queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_delta(delta: str) -> None:
            if delta:
                await delta_queue.put(delta)

        async def run_graph() -> AgentGraphResult:
            try:
                return await self._graph.run(
                    user_text=user_text,
                    session_memory=self._memory,
                    history=self._history,
                    on_delta=on_delta,
                )
            finally:
                await delta_queue.put(None)

        graph_task = asyncio.create_task(run_graph())
        full_response_parts: list[str] = []

        while True:
            delta = await delta_queue.get()
            if delta is None:
                break
            full_response_parts.append(delta)
            yield ConversationEvent(kind="assistant_delta", text=delta)

        retrieved_chunks: list[dict[str, object]] = []
        tool_calls: list[dict[str, object]] = []
        memory_summary = ""
        try:
            graph_result = await graph_task
            final_text = graph_result.response_text.strip()
            retrieved_chunks = list(graph_result.retrieved_chunks)
            tool_calls = list(graph_result.tool_calls)
            memory_summary = graph_result.memory_summary
        except Exception:
            logger.exception("LangGraph response generation failed")
            final_text = ""

        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_name = str(tool_call.get("name") or "").strip()
            if not tool_name:
                continue
            tool_arguments = tool_call.get("arguments")
            if not isinstance(tool_arguments, dict):
                tool_arguments = {}
            tool_result_summary = str(tool_call.get("result_summary") or "").strip()
            yield ConversationEvent(
                kind="tool_call",
                tool_name=tool_name,
                tool_arguments=tool_arguments,
                tool_result_summary=tool_result_summary or None,
            )

        if not final_text:
            final_text = "".join(full_response_parts).strip()
        if not final_text:
            final_text = "Sorry, I ran into an issue while generating the response."

        self._history.append({"role": "assistant", "content": final_text})
        self._history = self._history[-self._max_history_messages :]
        yield ConversationEvent(
            kind="assistant_complete",
            text=final_text,
            retrieved_chunks=retrieved_chunks or None,
            memory_summary=memory_summary or None,
        )
