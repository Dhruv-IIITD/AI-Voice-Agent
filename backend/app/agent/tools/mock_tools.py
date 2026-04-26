from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _store_path() -> Path:
    return Path(__file__).resolve().parents[3] / ".agent_store" / "mock_tickets.json"


def _load_tickets(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _save_tickets(path: Path, tickets: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(tickets, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def create_mock_ticket(title: str, description: str) -> dict[str, object]:
    normalized_title = title.strip() or "Support request"
    normalized_description = description.strip() or "No description provided."
    created_at = datetime.now(timezone.utc).isoformat()
    ticket = {
        "ticket_id": f"TICKET-{uuid4().hex[:8].upper()}",
        "title": normalized_title,
        "description": normalized_description,
        "status": "open",
        "created_at": created_at,
    }

    path = _store_path()
    tickets = _load_tickets(path)
    tickets.append(ticket)
    _save_tickets(path, tickets)
    return ticket
