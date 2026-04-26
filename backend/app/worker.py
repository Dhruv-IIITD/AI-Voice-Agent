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

            tts_queue: asyncio.Queue[str | None] = asyncio.Queue()
            tts_warning_sent = {"value": False}

            async def tts_worker() -> None:
                while True:
                    chunk = await tts_queue.get()
                    if chunk is None:
                        return

                    try:
                        audio = await self.text_to_speech.synthesize(chunk)
                    except Exception:
                        logger.exception(
                            "TTS synthesis failed provider=%s chunk_length=%s",
                            self.metadata.tts_provider,
                            len(chunk),
                        )
                        if not tts_warning_sent["value"]:
                            tts_warning_sent["value"] = True
                            await self.publish_assistant_warning(
                                "Voice playback is having trouble right now. Text responses are still available."
                            )
                        continue

                    if not audio.audio:
                        logger.warning(
                            "TTS returned empty audio provider=%s chunk_length=%s",
                            self.metadata.tts_provider,
                            len(chunk),
                        )
                        continue

                    try:
                        await self.tts_audio_player.play(audio.audio)
                    except Exception:
                        logger.exception(
                            "TTS playback failed provider=%s chunk_length=%s",
                            self.metadata.tts_provider,
                            len(chunk),
                        )
                        if not tts_warning_sent["value"]:
                            tts_warning_sent["value"] = True
                            await self.publish_assistant_warning(
                                "Voice playback is having trouble right now. Text responses are still available."
                            )
                        continue

            tts_task = asyncio.create_task(tts_worker())
            try:
                start_llm = time.perf_counter()
                final_text = ""
                retrieved_chunks: list[dict[str, object]] = []
                memory_summary = ""
                full_response_parts: list[str] = []
                tts_buffer = ""
                speaking_started = False
                min_sentence_chars = 24
                max_chunk_chars = 140

                def pop_flushable_chunk(buffer: str) -> tuple[str | None, str]:
                    if len(buffer) < min_sentence_chars:
                        return None, buffer

                    boundary = max(buffer.rfind("\n"), buffer.rfind("."), buffer.rfind("!"), buffer.rfind("?"))
                    if boundary != -1 and boundary + 1 >= min_sentence_chars:
                        cut = boundary + 1
                        return buffer[:cut], buffer[cut:]

                    if len(buffer) >= max_chunk_chars:
                        cut = buffer.rfind(" ", 0, max_chunk_chars)
                        if cut == -1:
                            cut = max_chunk_chars
                        return buffer[:cut], buffer[cut:]

                    return None, buffer

                async for event in self.conversation_session.stream_reply(user_text):
                    if event.kind == "tool_call":
                        logger.info("Publishing tool call to frontend tool_name=%s", event.tool_name)
                        await publish_voice_event(
                            self.room,
                            {
                                "type": "tool_call",
                                "toolName": event.tool_name,
                                "arguments": event.tool_arguments or {},
                                "resultSummary": event.tool_result_summary or "",
                            },
                        )
                        continue

                    if event.kind == "assistant_delta":
                        logger.info("Assistant delta emitted delta_length=%s", len(event.text))
                        full_response_parts.append(event.text)
                        tts_buffer += event.text
                        await publish_voice_event(
                            self.room,
                            {
                                "type": "assistant_delta",
                                "delta": event.text,
                            },
                        )

                        while True:
                            chunk, tts_buffer = pop_flushable_chunk(tts_buffer)
                            if chunk is None:
                                break

                            to_speak = chunk.strip()
                            if not to_speak:
                                continue

                            if not speaking_started:
                                speaking_started = True
                                await self.update_assistant_state("speaking")
                                logger.info(
                                    "Starting streaming TTS playback tts_provider=%s",
                                    self.metadata.tts_provider,
                                )

                            tts_queue.put_nowait(to_speak)
                        continue

                    if event.kind == "assistant_complete":
                        final_text = event.text
                        retrieved_chunks = list(event.retrieved_chunks or [])
                        memory_summary = str(event.memory_summary or "")
                        logger.info(
                            "Assistant complete text_length=%s rag_chunks=%s memory_summary_chars=%s",
                            len(final_text),
                            len(retrieved_chunks),
                            len(memory_summary),
                        )

                llm_latency_ms = (time.perf_counter() - start_llm) * 1000

                if not final_text:
                    final_text = "".join(full_response_parts).strip() or "I did not generate a response."

                # Finalize transcript on screen before playback starts
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

                if not tts_buffer.strip() and not speaking_started:
                    tts_buffer = final_text

                remainder = tts_buffer.strip()
                if remainder:
                    if not speaking_started:
                        speaking_started = True
                        await self.update_assistant_state("speaking")
                        logger.info(
                            "Starting streaming TTS playback tts_provider=%s",
                            self.metadata.tts_provider,
                        )
                    tts_queue.put_nowait(remainder)

                tts_queue.put_nowait(None)
                await tts_task

                logger.info("Assistant audio playback finished")
                await self.update_assistant_state("listening")
            finally:
                if not tts_task.done():
                    tts_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await tts_task

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
