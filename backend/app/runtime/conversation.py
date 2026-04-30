from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from app.agent.graph import VoiceAgentGraph
from app.agent.memory import SessionMemory
from app.agents.catalog import AgentDefinition

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConversationReply:
    text: str
    retrieved_chunks: list[dict[str, object]]
    memory_summary: str


class ConversationSession:
    _max_history_messages = 14
    _fallback_response = "Sorry, I ran into an issue while generating the response."

    def __init__(
        self,
        *,
        agent: AgentDefinition,
    ) -> None:
        self._agent = agent
        self._memory = SessionMemory(session_id=f"{agent.id}-{uuid4().hex[:8]}")
        self._history: list[dict[str, object]] = []
        self._graph = VoiceAgentGraph(agent=agent)

    async def reply(self, user_text: str) -> ConversationReply:
        # ConversationSession handles one user turn and returns one final response.
        logger.info("Conversation turn started agent=%s user_text=%s", self._agent.id, user_text)

        self._history.append({"role": "user", "content": user_text})
        self._history = self._history[-self._max_history_messages :]

        final_text = ""
        retrieved_chunks: list[dict[str, object]] = []
        memory_summary = ""
        try:
            graph_result = await self._graph.run(
                user_text=user_text,
                session_memory=self._memory,
                history=self._history,
            )
            final_text = graph_result.response_text.strip()
            retrieved_chunks = list(graph_result.retrieved_chunks)
            memory_summary = graph_result.memory_summary
        except Exception:
            logger.exception("LangGraph response generation failed")

        if not final_text:
            final_text = self._fallback_response

        self._history.append({"role": "assistant", "content": final_text})
        self._history = self._history[-self._max_history_messages :]

        return ConversationReply(
            text=final_text,
            retrieved_chunks=retrieved_chunks,
            memory_summary=memory_summary,
        )
