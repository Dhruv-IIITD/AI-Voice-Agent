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
    def __init__(
        self,
        *,
        session_id: str | None = None,
        max_recent_turns: int = 14,
        summary_trigger_turns: int = 10,
        summary_keep_recent: int = 8,
    ) -> None:
        self.session_id = session_id or f"session-{uuid4().hex[:12]}"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.max_recent_turns = max(6, max_recent_turns)
        self.summary_trigger_turns = max(6, summary_trigger_turns)
        self.summary_keep_recent = max(4, summary_keep_recent)

        self._turns: list[MemoryTurn] = []
        self._rolling_summary = ""
        logger.info("[Memory] Loaded session memory session_id=%s turns=%s", self.session_id, len(self._turns))

    @property
    def rolling_summary(self) -> str:
        return self._rolling_summary

    def add_user_turn(self, text: str) -> None:
        self._add_turn(role="user", text=text)
        logger.info("[Memory] Added user turn session_id=%s", self.session_id)

    def add_assistant_turn(self, text: str) -> None:
        self._add_turn(role="assistant", text=text)
        logger.info("[Memory] Added assistant turn session_id=%s", self.session_id)

    def get_recent_history(self, *, limit: int = 12) -> list[dict[str, object]]:
        turns = self._turns[-max(1, limit) :]
        return [{"role": turn.role, "content": turn.text} for turn in turns]

    def summarize_conversation(self) -> str:
        if not self._turns:
            return "No conversation has happened yet."

        recent_lines = [
            f"{turn.role.capitalize()}: {turn.text[:160]}"
            for turn in self._turns[-8:]
        ]
        recent_summary = " ".join(recent_lines).strip()
        if self._rolling_summary:
            return f"{self._rolling_summary} Recent turns: {recent_summary}".strip()
        return recent_summary

    def get_session_context(self, *, limit: int = 6) -> dict[str, object]:
        recent_turns = [
            {
                "role": turn.role,
                "text": turn.text,
                "created_at": turn.created_at,
            }
            for turn in self._turns[-max(1, limit) :]
        ]
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "rolling_summary": self._rolling_summary,
            "recent_turns": recent_turns,
        }

    def build_prompt_context(self) -> str:
        sections: list[str] = []
        if self._rolling_summary:
            sections.append(f"Rolling summary:\n{self._rolling_summary}")

        recent_turns = self.get_recent_history(limit=8)
        if recent_turns:
            lines = [
                f"{str(item.get('role', '')).capitalize()}: {str(item.get('content', ''))}"
                for item in recent_turns
            ]
            sections.append("Recent turns:\n" + "\n".join(lines))

        return "\n\n".join(sections).strip()

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
        self._compress_if_needed()

    def _compress_if_needed(self) -> None:
        if len(self._turns) <= self.summary_trigger_turns:
            return

        if len(self._turns) <= self.summary_keep_recent:
            return

        older_turns = self._turns[: -self.summary_keep_recent]
        summary_lines = [
            f"{turn.role.capitalize()}: {turn.text[:120]}"
            for turn in older_turns
        ]
        summary_fragment = " ".join(summary_lines).strip()
        if not summary_fragment:
            return

        if self._rolling_summary:
            combined = f"{self._rolling_summary} {summary_fragment}".strip()
        else:
            combined = summary_fragment

        self._rolling_summary = combined[-1400:]
        self._turns = self._turns[-self.summary_keep_recent :]
        logger.info("[Memory] Updated rolling summary session_id=%s chars=%s", self.session_id, len(self._rolling_summary))
