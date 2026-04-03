from __future__ import annotations

import json
from typing import Any

VOICE_EVENT_TOPIC = "voice-event"


async def publish_voice_event(room: Any, event: dict[str, Any]) -> None:
    payload = json.dumps(event).encode("utf-8")
    await room.local_participant.publish_data(payload, reliable=True, topic=VOICE_EVENT_TOPIC)

