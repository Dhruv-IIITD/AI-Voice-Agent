from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import NotRequired, TypedDict

from app.agent.memory import SessionMemory

DeltaCallback = Callable[[str], Awaitable[None]]
ChatHistoryMessage = dict[str, object]


class AgentState(TypedDict):
    user_text: str
    session_memory: SessionMemory
    history: Sequence[ChatHistoryMessage]
    response_text: str
    on_delta: NotRequired[DeltaCallback]
    memory_context: NotRequired[str]
    rag_context: NotRequired[str]
    retrieved_chunks: NotRequired[list[dict[str, object]]]
    selected_tool_name: NotRequired[str]
    selected_tool_arguments: NotRequired[dict[str, object]]
    tool_calls: NotRequired[list[dict[str, object]]]
    tool_context: NotRequired[str]
