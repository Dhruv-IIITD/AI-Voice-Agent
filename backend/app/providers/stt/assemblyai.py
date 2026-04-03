from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlencode

import websockets
from websockets.asyncio.client import ClientConnection

from app.providers.stt.base import BaseStreamingSTT, TranscriptEvent

logger = logging.getLogger(__name__)


class AssemblyAIStreamingSTT(BaseStreamingSTT):
    provider_name = "assemblyai"

    def __init__(self, *, api_key: str, speech_model: str) -> None:
        super().__init__()
        self._api_key = api_key
        self._speech_model = speech_model
        self._socket: ClientConnection | None = None
        self._receiver_task: asyncio.Task[None] | None = None
        
        self._buffer = b""
        self._target_size = int(self.sample_rate * 2 * 0.1)  # ~100 ms

    async def connect(self) -> None:
        query = urlencode(
            {
                "sample_rate": self.sample_rate,
                "speech_model": self._speech_model,
                "format_turns": "true",
                "end_utterance_silence_threshold": 1000,
            }
        )
        self._socket = await websockets.connect(
            f"wss://streaming.assemblyai.com/v3/ws?{query}",
            additional_headers={"Authorization": self._api_key},
            max_size=None,
        )
        self._receiver_task = asyncio.create_task(self._receive_messages())

    async def send_audio(self, pcm_chunk: bytes) -> None:
        if self._socket is None:
            raise RuntimeError("AssemblyAI websocket is not connected.")

        # accumulate
        self._buffer += pcm_chunk

        # send only when large enough
        if len(self._buffer) >= self._target_size:
            await self._socket.send(self._buffer)
            self._buffer = b""

    async def close(self) -> None:
        if self._socket is not None:
            await self._socket.close()
        if self._receiver_task is not None:
            await self._receiver_task
        else:
            await self.finish()

    async def _receive_messages(self) -> None:
        assert self._socket is not None
        try:
            async for message in self._socket:
                if isinstance(message, bytes):
                    continue
                payload = json.loads(message)
                transcript = (payload.get("transcript") or payload.get("text") or "").strip()
                if not transcript:
                    continue
                message_type = str(payload.get("type") or payload.get("message_type") or "").lower()
                is_final = bool(
                    payload.get("end_of_turn")
                    or payload.get("message_type") == "FinalTranscript"
                    or payload.get("is_final")
                    or payload.get("final")
                )
                await self.emit(
                    TranscriptEvent(
                        text=transcript,
                        is_final=is_final,
                        provider=self.provider_name,
                    )
                )
        except Exception:  # pragma: no cover - network behavior
            logger.exception("AssemblyAI receive loop failed")
        finally:
            await self.finish()

