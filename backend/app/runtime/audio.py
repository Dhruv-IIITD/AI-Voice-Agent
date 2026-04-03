from __future__ import annotations

from livekit import rtc


class AudioTrackPlayer:
    def __init__(
        self,
        *,
        source: rtc.AudioSource,
        sample_rate: int,
        num_channels: int,
        frame_ms: int,
    ) -> None:
        self._source = source
        self._sample_rate = sample_rate
        self._num_channels = num_channels
        self._samples_per_channel = int(sample_rate * frame_ms / 1000)
        self._frame_bytes = self._samples_per_channel * num_channels * 2

    async def play(self, pcm_audio: bytes) -> None:
        for start in range(0, len(pcm_audio), self._frame_bytes):
            chunk = pcm_audio[start : start + self._frame_bytes]
            if len(chunk) < self._frame_bytes:
                chunk = chunk.ljust(self._frame_bytes, b"\0")

            frame = rtc.AudioFrame.create(
                self._sample_rate,
                self._num_channels,
                self._samples_per_channel,
            )
            frame.data.cast("B")[:] = chunk
            await self._source.capture_frame(frame)

