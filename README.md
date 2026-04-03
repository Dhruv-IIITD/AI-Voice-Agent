# Voice Engineering Take Home Assignment

This repository contains a browser-based voice AI proof of concept with:

- a Next.js frontend for agent selection, route-based navigation, and browser microphone sessions,
- a FastAPI backend for session management,
- a LiveKit Python worker for room orchestration,
- custom STT adapters for Deepgram and AssemblyAI,
- custom TTS adapters for ElevenLabs and Cartesia,
- custom LLM + tool orchestration built in application code through an OpenRouter free model.

## Project layout

```text
backend/   FastAPI app, LiveKit worker, provider adapters, tools
frontend/  Next.js browser client
docs/      Architecture note
```

## Demo flow

1. Open the web app.
2. Choose either the Support Agent or Scheduling Agent.
3. Choose the STT and TTS providers.
4. Start the LiveKit session from the browser.
5. Speak into the microphone.
6. The worker transcribes speech through your chosen STT adapter.
7. The backend tool/LLM orchestration decides whether to call a tool.
8. The assistant response is streamed through application code, synthesized by the chosen TTS adapter, and played back in the browser.

## Requirements

- Python 3.11+
- Node 20+
- A LiveKit Cloud project
- one OpenRouter API key for the demo LLM
- At least one key per STT provider you want to test
- At least one key per TTS provider you want to test

## Setup

### 1. Backend

Use a virtual environment. The LiveKit agent runtime installs newer `numpy` and `protobuf` versions, so isolating dependencies is strongly recommended.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
copy .env.example .env
```

Fill in these required values in `backend/.env`:

- `LIVEKIT_WS_URL`
- `LIVEKIT_API_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- if you want to avoid paid OpenRouter models entirely, keep `OPENROUTER_REQUIRE_FREE=true` and use `OPENROUTER_MODEL=qwen/qwen3.6-plus:free` or another model ending in `:free`
- the provider keys you plan to use, such as `DEEPGRAM_API_KEY` and `ELEVENLABS_API_KEY`

Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run the worker in a second terminal:

```bash
cd backend
.venv\Scripts\activate
python -m app.runtime.worker dev
```

### 2. Frontend

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8000/api` by default and serves the voice console on `/`.

### Frontend-only preview

If you just want to inspect the UI without setting up API keys or the backend, you can run only the frontend:

```bash
cd frontend
npm install
npm run dev
```

When the backend is unavailable, the frontend automatically falls back to a local mock mode with hardcoded agents and a simulated transcript/session flow.

## Verification

The current repo was verified with:

- `python -m compileall app` inside [backend](C:/Dhruv/Projects/Voice-app/codex/backend)
- `npm run build` inside [frontend](C:/Dhruv/Projects/Voice-app/codex/frontend)

## Important implementation notes

- LiveKit is used for room/session orchestration and worker dispatch only.
- STT, TTS, LLM streaming, and tool execution all run through application-owned abstractions.
- Tool calling is implemented with a separate planning pass and a streamed answer pass to keep orchestration logic explicit.
- Transcript and assistant state updates are sent back to the browser over LiveKit data messages.
- The voice protocol is half-duplex: the browser mic is active only while the assistant is in the `listening` state, and the worker drops inbound audio while the assistant is thinking or speaking.

## Simplifications

- The demo stores conversation state in memory per room worker.
- Tool data is hardcoded for the take-home scope.
- TTS is synthesized after the assistant text stream completes, then played into a LiveKit audio track.
- Error handling is intentionally lightweight and optimized for the happy path.

## What I would improve next

- Add sentence-level incremental TTS to reduce reply latency.
- Add stronger turn-taking and interruption handling.
- Add richer observability around provider latency and failures.
- Add tests for tool orchestration and provider selection behavior.
- Add a small persisted conversation/session store for debugging.

See [docs/ARCHITECTURE.md](C:/Dhruv/Projects/Voice-app/codex/docs/ARCHITECTURE.md) for the module breakdown.
