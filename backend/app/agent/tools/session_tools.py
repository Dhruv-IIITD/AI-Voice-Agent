from __future__ import annotations

from app.agent.memory import SessionMemory


def summarize_conversation(memory: SessionMemory) -> dict[str, object]:
    summary = memory.summarize_conversation()
    return {
        "summary": summary,
    }


def get_session_context(memory: SessionMemory) -> dict[str, object]:
    context = memory.get_session_context(limit=8)
    summary = context.get("rolling_summary") or memory.summarize_conversation()
    return {
        "session": context,
        "summary": summary,
    }
