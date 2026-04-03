from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SynthesizedAudio:
    audio: bytes
    sample_rate: int
    num_channels: int = 1


class BaseTTSClient(ABC):
    sample_rate: int
    num_channels: int = 1

    @abstractmethod
    async def synthesize(self, text: str) -> SynthesizedAudio:
        raise NotImplementedError

