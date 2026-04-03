from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlencode

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.asyncio.client import ClientConnection

from app.providers.stt.base import BaseStreamingSTT, TranscriptEvent

logger = logging.getLogger(__name__)


class DeepgramStreamingSTT(BaseStreamingSTT):
    provider_name = "deepgram"

    def __init__(self, *, api_key: str, model: str) -> None:
        super().__init__()
        self._api_key = api_key
        self._model = model
        self._socket: ClientConnection | None = None
        self._receiver_task: asyncio.Task[None] | None = None
        self._keepalive_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        query = urlencode(
            {
                "model": self._model,
                "encoding": "linear16",
                "sample_rate": self.sample_rate,
                "channels": self.num_channels,
                "interim_results": "true",
                "endpointing": 300,
                "smart_format": "true",
            }
        )
        self._socket = await websockets.connect(
            f"wss://api.deepgram.com/v1/listen?{query}",
            additional_headers={"Authorization": f"Token {self._api_key}"},
            max_size=None,
        )
        self._receiver_task = asyncio.create_task(self._receive_messages())
        self._keepalive_task = asyncio.create_task(self._send_keepalives())

    async def send_audio(self, pcm_chunk: bytes) -> None:
        if self._socket is None:
            raise RuntimeError("Deepgram websocket is not connected.")
        await self._socket.send(pcm_chunk)

    async def close(self) -> None:
        if self._socket is not None:
            try:
                await self._socket.send(json.dumps({"type": "CloseStream"}))
            except Exception:  # pragma: no cover - provider close behavior
                pass
            await self._socket.close()
        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
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
                if payload.get("type") != "Results":
                    continue
                alternatives = ((payload.get("channel") or {}).get("alternatives") or [{}])
                transcript = (alternatives[0].get("transcript") or "").strip()
                if not transcript:
                    continue
                await self.emit(
                    TranscriptEvent(
                        text=transcript,
                        is_final=bool(payload.get("speech_final") or payload.get("is_final")),
                        provider=self.provider_name,
                    )
                )
        except ConnectionClosed as exc:  # pragma: no cover - network behavior
            if "NET-0001" in str(exc) or "did not receive audio data" in str(exc):
                logger.warning("Deepgram stream closed after silence timeout")
            else:
                logger.exception("Deepgram receive loop closed unexpectedly")
        except Exception:  # pragma: no cover - network behavior
            logger.exception("Deepgram receive loop failed")
        finally:
            await self.finish()

    async def _send_keepalives(self) -> None:
        assert self._socket is not None
        try:
            while True:
                await asyncio.sleep(3)
                await self._socket.send(json.dumps({"type": "KeepAlive"}))
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - network behavior
            logger.exception("Deepgram keepalive loop failed")
