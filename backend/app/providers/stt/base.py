from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptEvent:
    text: str
    is_final: bool
    provider: str


class BaseStreamingSTT(ABC):
    provider_name: str
    sample_rate: int = 48_000
    num_channels: int = 1

    def __init__(self) -> None:
        self._events: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()

    async def emit(self, event: TranscriptEvent) -> None:
        await self._events.put(event)

    async def events(self) -> AsyncIterator[TranscriptEvent]:
        while True:
            item = await self._events.get()
            if item is None:
                break
            yield item

    async def finish(self) -> None:
        await self._events.put(None)

    @abstractmethod
    async def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_audio(self, pcm_chunk: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

