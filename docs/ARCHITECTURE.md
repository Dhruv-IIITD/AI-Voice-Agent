# Architecture Note

## Overview

The project is intentionally split into three layers:

1. Browser client in [frontend](C:/Dhruv/Projects/Voice-app/codex/frontend)
2. FastAPI management API in [backend/app](C:/Dhruv/Projects/Voice-app/codex/backend/app)
3. LiveKit worker runtime in [backend/app/runtime](C:/Dhruv/Projects/Voice-app/codex/backend/app/runtime)

LiveKit Cloud is responsible for the real-time room and worker dispatch. The application owns the intelligence path.

## Request and media flow

1. The frontend fetches available agents from `GET /api/agents`.
2. The user selects an agent plus STT/TTS providers and posts to `POST /api/sessions`.
3. [session_manager.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/livekit/session_manager.py) creates a room, dispatches the named LiveKit worker, and returns a browser token.
4. The frontend connects to LiveKit with `livekit-client` and publishes the microphone track.
5. [worker.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/runtime/worker.py) joins the same room, subscribes to the browser audio track, and streams PCM frames into the selected STT adapter.
6. Final transcripts are handed to [conversation.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/runtime/conversation.py).
7. The conversation layer performs a tool-planning pass with the LLM, executes any requested tools via [registry.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/tools/registry.py), and then streams the final assistant answer through the LLM client.
8. The selected TTS adapter synthesizes the final text to PCM audio.
9. The worker publishes PCM frames to a LiveKit local audio track so the browser hears the response.
10. Transcript/status/tool events are sent to the frontend through LiveKit data messages for a simple real-time UI.
11. The runtime follows a half-duplex voice protocol: user audio is only forwarded to STT while the assistant is in `listening`, and the browser mic is paused while the assistant is thinking or speaking.

## Module boundaries

### FastAPI management layer

- [main.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/main.py): app bootstrap, CORS, router mounting
- [routes.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/api/routes.py): agent list and session creation endpoints
- [session_manager.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/livekit/session_manager.py): room provisioning, agent dispatch, token creation

### Agent and orchestration layer

- [catalog.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/agents/catalog.py): hardcoded agent personas
- [conversation.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/runtime/conversation.py): conversation history, tool planning, streamed final answer
- [registry.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/tools/registry.py): tool schemas and execution

### Provider adapters

- [factory.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/providers/stt/factory.py): STT provider selection
- [deepgram.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/providers/stt/deepgram.py): Deepgram streaming adapter
- [assemblyai.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/providers/stt/assemblyai.py): AssemblyAI streaming adapter
- [factory.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/providers/tts/factory.py): TTS provider selection
- [elevenlabs.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/providers/tts/elevenlabs.py): ElevenLabs PCM streaming adapter
- [cartesia.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/providers/tts/cartesia.py): Cartesia bytes adapter
- [openrouter_provider.py](C:/Dhruv/Projects/Voice-app/codex/backend/app/providers/llm/openrouter_provider.py): OpenRouter planning and streamed answer generation through an OpenAI-compatible client

### Frontend

- [layout.tsx](C:/Dhruv/Projects/Voice-app/codex/frontend/src/app/layout.tsx): global layout shell
- [page.tsx](C:/Dhruv/Projects/Voice-app/codex/frontend/src/app/page.tsx): main voice console route
- [voice-workspace.tsx](C:/Dhruv/Projects/Voice-app/codex/frontend/src/features/voice/components/voice-workspace.tsx): main client-side session console
- [use-voice-session.ts](C:/Dhruv/Projects/Voice-app/codex/frontend/src/features/voice/hooks/use-voice-session.ts): LiveKit room lifecycle, mic controls, transcript state
- [transcript-panel.tsx](C:/Dhruv/Projects/Voice-app/codex/frontend/src/features/voice/components/transcript-panel.tsx): transcript rendering

## Design choices

- Explicit provider wrappers keep LiveKit focused on orchestration, not intelligence ownership.
- A separate tool-planning pass keeps tool execution understandable and easy to debug.
- Agent prompts and tool execution are scoped per persona so each agent only sees and uses its own allowed tool inventory.
- Browser UI state is driven by room connection plus worker data events, which keeps the frontend simple and observable.
- Agent configuration is intentionally hardcoded for the take-home timebox.

## Tradeoffs

- The response text is streamed immediately, but audio synthesis starts after the full answer completes.
- The STT adapters favor straightforward WebSocket integration over advanced endpoint tuning.
- The project currently targets the happy path and does not yet include resilience patterns like reconnects, retries, or provider failover.
