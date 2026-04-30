from __future__ import annotations

from collections.abc import Sequence
from typing import NotRequired, TypedDict

from app.agent.memory import SessionMemory

ChatHistoryMessage = dict[str, object]


class AgentState(TypedDict):
    user_text: str
    session_memory: SessionMemory
    history: Sequence[ChatHistoryMessage]
    response_text: NotRequired[str]
    rag_context: NotRequired[str]
    retrieved_chunks: NotRequired[list[dict[str, object]]]
    memory_summary: NotRequired[str]
