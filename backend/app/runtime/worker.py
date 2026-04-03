from __future__ import annotations

import asyncio
import logging
import os

from livekit import rtc
from livekit.agents import AgentServer, AutoSubscribe, JobContext, cli

from app.agents.catalog import get_agent
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.providers.llm.factory import build_llm_client
from app.providers.stt.base import TranscriptEvent
from app.providers.stt.factory import build_stt_provider
from app.providers.tts.factory import build_tts_provider
from app.runtime.audio import AudioTrackPlayer
from app.runtime.conversation import ConversationSession
from app.runtime.events import publish_voice_event
from app.runtime.session_metadata import SessionMetadata
from app.tools.registry import ToolRegistry

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
os.environ.setdefault("LIVEKIT_URL", settings.livekit_ws_url)
os.environ.setdefault("LIVEKIT_API_KEY", settings.livekit_api_key)
os.environ.setdefault("LIVEKIT_API_SECRET", settings.livekit_api_secret)
os.environ.setdefault("LIVEKIT_LOG_LEVEL", settings.log_level.upper())
server = AgentServer(
    ws_url=settings.livekit_ws_url,
    api_key=settings.livekit_api_key,
    api_secret=settings.livekit_api_secret,
    log_level=settings.log_level.upper(),
)

class BrowserVoiceWorker:
    def __init__(self, *, ctx: JobContext, metadata: SessionMetadata) -> None:
        self._ctx = ctx
        self._room = ctx.room
        self._metadata = metadata
        self._agent = get_agent(metadata.agent_id)
        self._stt = build_stt_provider(settings, metadata.stt_provider)
        self._tts = build_tts_provider(settings, metadata.tts_provider)
        self._conversation = ConversationSession(
            agent=self._agent,
            llm_client=build_llm_client(settings),
            tool_registry=ToolRegistry(),
        )
        self._response_lock = asyncio.Lock()
        self._audio_source = rtc.AudioSource(
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
        )
        self._audio_track = rtc.LocalAudioTrack.create_audio_track("assistant-audio", 
                                                                   self._audio_source)
        self._player = AudioTrackPlayer(
            source=self._audio_source,
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
            frame_ms=settings.audio_frame_ms,
        )
        self._input_gate = asyncio.Event()
        self._audio_track_ready = asyncio.Event()
        self._consumer_task: asyncio.Task[None] | None = None
        self._transcript_task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        logger.info(
            "Worker run started room_name=%s participant_identity=%s stt=%s tts=%s",
            self._metadata.room_name,
            self._metadata.participant_identity,
            self._metadata.stt_provider,
            self._metadata.tts_provider,
        )
        await self._ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
        logger.info("Worker connected to room, publishing assistant audio track")
        await self._room.local_participant.publish_track(self._audio_track, rtc.TrackPublishOptions())
        await publish_voice_event(
            self._room,
            {
                "type": "session_ready",
                "agentId": self._agent.id,
                "agentName": self._agent.name,
                "roomName": self._metadata.room_name,
            },
        )
        await self._set_assistant_state("listening")

        participant = await self._ctx.wait_for_participant(identity=self._metadata.participant_identity)
        logger.info("Target participant joined identity=%s", participant.identity)

        @self._room.on("track_subscribed")
        def handle_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            remote_participant: rtc.RemoteParticipant,
        ) -> None:
            logger.info(
                "Track subscribed callback participant=%s publication_kind=%s track_sid=%s",
                remote_participant.identity,
                publication.kind,
                getattr(track, "sid", None),
            )
            if remote_participant.identity != participant.identity:
                return
            if publication.kind != rtc.TrackKind.KIND_AUDIO:
                return
            self._start_audio_consumer(track)

        for publication in participant.track_publications.values():
            if publication.kind != rtc.TrackKind.KIND_AUDIO:
                continue
            logger.info(
                "Inspecting existing publication kind=%s subscribed=%s",
                publication.kind,
                publication.subscribed,
            )
            publication.set_subscribed(True)
            if publication.track is not None and self._consumer_task is None:
                logger.info("Starting audio consumer from existing publication")
                self._start_audio_consumer(publication.track)
                break

        if self._consumer_task is None:
            logger.info(
                "No audio track available yet for participant=%s, waiting for microphone publication",
                participant.identity,
            )
            try:
                await asyncio.wait_for(self._audio_track_ready.wait(), timeout=15)
            except TimeoutError as exc:
                logger.error(
                    "Timed out waiting for remote audio track participant=%s publications=%s",
                    participant.identity,
                    [
                        {
                            "kind": publication.kind,
                            "subscribed": publication.subscribed,
                            "has_track": publication.track is not None,
                        }
                        for publication in participant.track_publications.values()
                    ],
                )
                raise RuntimeError("No remote audio track became available for the browser participant.") from exc

        await self._consumer_task
        if self._transcript_task is not None:
            await self._transcript_task

    def _start_audio_consumer(self, track: rtc.Track) -> None:
        if self._consumer_task and not self._consumer_task.done():
            return
        logger.info("Creating audio consumer task track_sid=%s", getattr(track, "sid", None))
        self._consumer_task = asyncio.create_task(self._consume_audio_track(track))
        self._audio_track_ready.set()

    async def _consume_audio_track(self, track: rtc.Track) -> None:
        logger.info("Connecting STT provider=%s", self._metadata.stt_provider)
        await self._stt.connect()
        logger.info("STT connected, starting transcript consumer")
        self._transcript_task = asyncio.create_task(self._consume_transcripts())
        audio_stream = rtc.AudioStream(
            track,
            sample_rate=self._stt.sample_rate,
            num_channels=self._stt.num_channels,
            frame_size_ms=settings.audio_frame_ms,
        )
        try:
            async for event in audio_stream:
                if not self._input_gate.is_set():
                    continue
                await self._stt.send_audio(event.frame.data.cast("B").tobytes())
        finally:
            logger.info("Audio stream closed, shutting down STT")
            await audio_stream.aclose()
            await self._stt.close()

    async def _consume_transcripts(self) -> None:
        last_partial = ""
        async for event in self._stt.events():
            if not self._input_gate.is_set():
                last_partial = ""
                continue
            if event.is_final:
                final_text = event.text.strip()
                if not final_text:
                    continue
                logger.info("Final transcript received provider=%s text=%s", event.provider, final_text)
                await publish_voice_event(
                    self._room,
                    {
                        "type": "user_transcript",
                        "text": final_text,
                        "final": True,
                        "provider": event.provider,
                    },
                )
                await self._handle_user_turn(final_text)
                last_partial = ""
                continue

            if event.text == last_partial:
                continue
            last_partial = event.text
            logger.info("Partial transcript received provider=%s text=%s", event.provider, event.text)
            await publish_voice_event(
                self._room,
                {
                    "type": "user_transcript",
                    "text": event.text,
                    "final": False,
                    "provider": event.provider,
                },
            )

    async def _handle_user_turn(self, user_text: str) -> None:
        async with self._response_lock:
            logger.info("Handling user turn text=%s", user_text)
            await self._set_assistant_state("thinking")

            final_text = ""
            async for event in self._conversation.stream_reply(user_text):
                if event.kind == "tool_call":
                    logger.info("Publishing tool call to frontend tool_name=%s", event.tool_name)
                    await publish_voice_event(
                        self._room,
                        {
                            "type": "tool_call",
                            "toolName": event.tool_name,
                            "arguments": event.tool_arguments or {},
                        },
                    )
                    continue

                if event.kind == "assistant_delta":
                    logger.info("Assistant delta emitted delta_length=%s", len(event.text))
                    await publish_voice_event(
                        self._room,
                        {
                            "type": "assistant_delta",
                            "delta": event.text,
                        },
                    )
                    continue

                if event.kind == "assistant_complete":
                    final_text = event.text
                    logger.info("Assistant complete text_length=%s", len(final_text))

            if not final_text:
                final_text = "I did not generate a response."

            await self._set_assistant_state("speaking")
            logger.info("Starting TTS synthesis tts_provider=%s", self._metadata.tts_provider)
            audio = await self._tts.synthesize(final_text)
            logger.info("TTS synthesis finished audio_bytes=%s", len(audio.audio))
            await self._player.play(audio.audio)
            logger.info("Assistant audio playback finished")
            await publish_voice_event(
                self._room,
                {
                    "type": "assistant_complete",
                    "text": final_text,
                },
            )
            await self._set_assistant_state("listening")

    async def _set_assistant_state(self, state: str) -> None:
        if state == "listening":
            self._input_gate.set()
        else:
            self._input_gate.clear()

        await publish_voice_event(
            self._room,
            {
                "type": "assistant_state",
                "state": state,
            },
        )


@server.rtc_session(agent_name=settings.livekit_agent_name)
async def browser_voice_session(ctx: JobContext) -> None:
    metadata = SessionMetadata.model_validate_json(ctx.job.metadata)
    worker = BrowserVoiceWorker(ctx=ctx, metadata=metadata)
    logger.info("Starting room job %s for agent %s", metadata.room_name, metadata.agent_id)
    await worker.run()


def main() -> None:
    cli.run_app(server)


if __name__ == "__main__":
    main()
