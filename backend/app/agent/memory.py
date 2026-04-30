from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MemoryTurn:
    role: str
    text: str
    created_at: str


class SessionMemory:
    """Lightweight session memory for summaries and debugging."""

    def __init__(self, *, session_id: str | None = None, max_recent_turns: int = 16) -> None:
        self.session_id = session_id or f"session-{uuid4().hex[:12]}"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.max_recent_turns = max(4, max_recent_turns)
        self._turns: list[MemoryTurn] = []
        logger.info("[Memory] Loaded session memory session_id=%s turns=%s", self.session_id, len(self._turns))

    def add_user_turn(self, text: str) -> None:
        self._add_turn(role="user", text=text)

    def add_assistant_turn(self, text: str) -> None:
        self._add_turn(role="assistant", text=text)

    def summarize_conversation(self) -> str:
        if not self._turns:
            return ""
        lines = [f"{turn.role.capitalize()}: {turn.text[:160]}" for turn in self._turns[-8:]]
        return " ".join(lines).strip()

    def _add_turn(self, *, role: str, text: str) -> None:
        normalized = text.strip()
        if not normalized:
            return
        self._turns.append(
            MemoryTurn(
                role=role,
                text=normalized,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        if len(self._turns) > self.max_recent_turns:
            self._turns = self._turns[-self.max_recent_turns :]
