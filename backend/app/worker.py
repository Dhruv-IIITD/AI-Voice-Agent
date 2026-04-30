from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time

from livekit import rtc
from livekit.agents import AgentServer, AutoSubscribe, JobContext, cli

from app.agents.catalog import get_agent
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.providers.stt.factory import build_stt_provider
from app.providers.tts.factory import build_tts_provider
from app.runtime.audio import AudioTrackPlayer
from app.runtime.conversation import ConversationSession
from app.runtime.events import publish_voice_event
from app.runtime.session_metadata import SessionMetadata

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

class AIVoiceWorker:
    def __init__(self, *, ctx:JobContext, metadata:SessionMetadata) -> None:
        
        self.ctx = ctx
        self.room = ctx.room
        self.metadata = metadata

        self.agent = get_agent(metadata.agent_id)
        try:
            self.speech_to_text = build_stt_provider(settings, metadata.stt_provider)
        except Exception as exc:
            message = (
                f"STT provider '{metadata.stt_provider}' initialization failed. "
                "Check provider configuration and API keys."
            )
            logger.exception(message)
            raise RuntimeError(message) from exc

        try:
            self.text_to_speech = build_tts_provider(settings, metadata.tts_provider)
        except Exception as exc:
            message = (
                f"TTS provider '{metadata.tts_provider}' initialization failed. "
                "Check provider configuration and API keys."
            )
            logger.exception(message)
            raise RuntimeError(message) from exc
        
        self.conversation_session = ConversationSession(
            agent=self.agent,
        )

        self.response_lock = asyncio.Lock()

        # 
        self.assistant_audio_source = rtc.AudioSource(
            sample_rate=self.text_to_speech.sample_rate,
            num_channels=self.text_to_speech.num_channels,
        )

        self.assistant_audio_track = rtc.LocalAudioTrack.create_audio_track("assistant-audio", 
                                                                   self.assistant_audio_source)
        
        self.tts_audio_player = AudioTrackPlayer(
            source=self.assistant_audio_source,
            sample_rate=self.text_to_speech.sample_rate,
            num_channels=self.text_to_speech.num_channels,
            frame_ms=settings.audio_frame_ms,
        )

        self.user_input_enabled = asyncio.Event()
        self.remote_audio_ready = asyncio.Event()

        self.audio_consumer_task: asyncio.Task[None] | None = None
        self.transcript_task: asyncio.Task[None] | None = None

    async def start_session(self) -> None:
        logger.info(
            "Worker run started room_name=%s participant_identity=%s speech_to_text=%s text_to_speech=%s",
            self.metadata.room_name,
            self.metadata.participant_identity,
            self.metadata.stt_provider,
            self.metadata.tts_provider,
        )
        await self.ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)

        logger.info("Worker connected to room, publishing assistant audio track")
        await self.room.local_participant.publish_track(self.assistant_audio_track, rtc.TrackPublishOptions())

        await publish_voice_event(
            self.room,
            {
                "type": "session_ready",
                "agentId": self.agent.id,
                "agentName": self.agent.name,
                "roomName": self.metadata.room_name,
            },
        )
        await self.update_assistant_state("listening")

        participant = await self.ctx.wait_for_participant(identity=self.metadata.participant_identity)
        logger.info("Target participant joined identity=%s", participant.identity)

        @self.room.on("track_subscribed")
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
            self.start_audio_stream_processing(track)

        for publication in participant.track_publications.values():
            if publication.kind != rtc.TrackKind.KIND_AUDIO:
                continue
            logger.info(
                "Inspecting existing publication kind=%s subscribed=%s",
                publication.kind,
                publication.subscribed,
            )
            publication.set_subscribed(True)
            if publication.track is not None and self.audio_consumer_task is None:
                logger.info("Starting audio consumer from existing publication")
                self.start_audio_stream_processing(publication.track)
                break

        if self.audio_consumer_task is None:
            logger.info(
                "No audio track available yet for participant=%s, waiting for microphone publication",
                participant.identity,
            )
            try:
                await asyncio.wait_for(self.remote_audio_ready.wait(), timeout=15)
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

        await self.audio_consumer_task
        if self.transcript_task is not None:
            await self.transcript_task

    def start_audio_stream_processing(self, track: rtc.Track) -> None:
        if self.audio_consumer_task and not self.audio_consumer_task.done():
            return
        logger.info("Creating audio consumer task track_sid=%s", getattr(track, "sid", None))
        self.audio_consumer_task = asyncio.create_task(self.process_audio_stream(track))
        self.remote_audio_ready.set()

    async def process_audio_stream(self, track: rtc.Track) -> None:
        try:
            logger.info("Connecting STT provider=%s", self.metadata.stt_provider)
            await self.speech_to_text.connect()
            logger.info("STT connected, starting transcript consumer")

            self.transcript_task = asyncio.create_task(self.handle_transcript_stream())

            audio_stream = rtc.AudioStream(
                track,
                sample_rate=self.speech_to_text.sample_rate,
                num_channels=self.speech_to_text.num_channels,
                frame_size_ms=settings.audio_frame_ms,
            )

            try:
                async for event in audio_stream:
                    audio_bytes = event.frame.data.cast("B").tobytes()
                    if not self.user_input_enabled.is_set():
                        # Feed silence to STT
                        await self.speech_to_text.send_audio(b"\x00" * len(audio_bytes))
                        continue
                    await self.speech_to_text.send_audio(audio_bytes)
            finally:
                logger.info("Audio stream closed, shutting down STT")
                await audio_stream.aclose()
                await self.speech_to_text.close()
        except Exception:
            logger.exception("STT provider runtime failure provider=%s", self.metadata.stt_provider)
            await self.publish_assistant_warning(
                "Speech recognition is currently unavailable. Please reconnect and try again."
            )
            with contextlib.suppress(Exception):
                await self.speech_to_text.close()
            await self.update_assistant_state("disconnected")

    async def handle_transcript_stream(self) -> None:
        last_partial = ""
        stt_start_time = None
        async for event in self.speech_to_text.events():
            if not self.user_input_enabled.is_set():
                last_partial = ""
                stt_start_time = None
                continue
            
            if stt_start_time is None:
                stt_start_time = time.perf_counter()

            if event.is_final:
                stt_latency_ms = (time.perf_counter() - stt_start_time) * 1000 if stt_start_time else 0
                stt_start_time = None
                final_text = event.text.strip()
                if not final_text:
                    continue
                logger.info("Final transcript received provider=%s text=%s", event.provider, final_text)
                await publish_voice_event(
                    self.room,
                    {
                        "type": "user_transcript",
                        "text": final_text,
                        "final": True,
                        "provider": event.provider,
                        "stt_latency_ms": round(stt_latency_ms),
                    },
                )
                try:
                    await self.generate_and_stream_response(final_text)
                except Exception:
                    logger.exception("Unhandled error processing user turn")
                    await self.update_assistant_state("listening")
                last_partial = ""
                continue

            if event.text == last_partial:
                continue
            last_partial = event.text
            logger.info("Partial transcript received provider=%s text=%s", event.provider, event.text)
            await publish_voice_event(
                self.room,
                {
                    "type": "user_transcript",
                    "text": event.text,
                    "final": False,
                    "provider": event.provider,
                },
            )

    async def generate_and_stream_response(self, user_text: str) -> None:
        async with self.response_lock:
            logger.info("Handling user turn text=%s", user_text)
            await self.update_assistant_state("thinking")
            start_llm = time.perf_counter()
            final_text = ""
            retrieved_chunks: list[dict[str, object]] = []
            memory_summary = ""

            reply = await self.conversation_session.reply(user_text)
            final_text = str(reply.text or "").strip()
            retrieved_chunks = list(reply.retrieved_chunks or [])
            memory_summary = str(reply.memory_summary or "")

            llm_latency_ms = (time.perf_counter() - start_llm) * 1000
            if not final_text:
                final_text = "I did not generate a response."

            logger.info(
                "Assistant complete text_length=%s rag_chunks=%s memory_summary_chars=%s",
                len(final_text),
                len(retrieved_chunks),
                len(memory_summary),
            )

            await publish_voice_event(
                self.room,
                {
                    "type": "assistant_complete",
                    "text": final_text,
                    "llm_latency_ms": round(llm_latency_ms),
                    "retrieved_chunks": retrieved_chunks,
                    "memory_summary": memory_summary,
                },
            )

            await self.update_assistant_state("speaking")
            logger.info(
                "Starting single-pass TTS playback tts_provider=%s text_length=%s",
                self.metadata.tts_provider,
                len(final_text),
            )

            tts_warning_message = "Voice playback is having trouble right now. Text responses are still available."
            try:
                audio = await self.text_to_speech.synthesize(final_text)
            except Exception:
                logger.exception(
                    "TTS synthesis failed provider=%s text_length=%s",
                    self.metadata.tts_provider,
                    len(final_text),
                )
                await self.publish_assistant_warning(tts_warning_message)
                await self.update_assistant_state("listening")
                return

            if not audio.audio:
                logger.warning(
                    "TTS returned empty audio provider=%s text_length=%s",
                    self.metadata.tts_provider,
                    len(final_text),
                )
                await self.publish_assistant_warning(tts_warning_message)
                await self.update_assistant_state("listening")
                return

            try:
                await self.tts_audio_player.play(audio.audio)
                logger.info("Assistant audio playback finished")
            except Exception:
                logger.exception(
                    "TTS playback failed provider=%s text_length=%s",
                    self.metadata.tts_provider,
                    len(final_text),
                )
                await self.publish_assistant_warning(tts_warning_message)
            finally:
                await self.update_assistant_state("listening")

    async def update_assistant_state(self, state: str) -> None:
        if state == "listening":
            self.user_input_enabled.set()
        else:
            self.user_input_enabled.clear()

        await publish_voice_event(
            self.room,
            {
                "type": "assistant_state",
                "state": state,
            },
        )

    async def publish_assistant_warning(self, message: str) -> None:
        logger.warning("Publishing assistant warning message=%s", message)
        await publish_voice_event(
            self.room,
            {
                "type": "assistant_warning",
                "message": message,
            },
        )


@server.rtc_session(agent_name=settings.livekit_agent_name)
async def ai_voice_session(ctx: JobContext) -> None:
    metadata = SessionMetadata.model_validate_json(ctx.job.metadata)
    worker = AIVoiceWorker(ctx=ctx, metadata=metadata)
    logger.info("Starting room job %s for agent %s", metadata.room_name, metadata.agent_id)
    await worker.start_session()


def main() -> None:
    cli.run_app(server)


if __name__ == "__main__":
    main()
