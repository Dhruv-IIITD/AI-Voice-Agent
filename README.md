# AI Voice Agent

## Project Description
This project is a real-time, browser-based voice AI platform that supports multi-provider STT/TTS, LangGraph-based orchestration, RAG over uploaded documents, and session memory.

## Problem It Solves
Most voice assistants either feel high-latency or have rigid pipelines. This system focuses on a practical developer architecture that keeps voice interactions responsive while supporting grounded document answers and agent workflows.

## Key Features
- Real-time voice sessions from browser microphone to spoken assistant reply.
- LangChain + LangGraph orchestration for structured backend response generation.
- RAG over uploaded `.txt` and `.pdf` documents with local Chroma vector storage.
- Session-scoped memory for follow-up and conversational continuity.
- Final-response LLM generation with single-pass TTS playback.
- Session observability via transcript events and latency metrics (`STT`, `LLM`, optional `TTS` fields).

## Architecture (Text Diagram)
```text
Browser Microphone
  -> LiveKit Room
  -> Python Voice Worker
  -> STT Provider (Deepgram/AssemblyAI)
  -> LangGraph Agent Orchestrator
       -> Session Memory
       -> RAG Retrieval (if relevant)
       -> LangChain Chat Model (Groq)
  -> Final Assistant Text Event
  -> TTS Provider (ElevenLabs/Cartesia)
  -> LiveKit Audio Track
  -> Browser Playback
```

## Tech Stack
- Frontend: `Next.js`, `TypeScript`, `LiveKit Client`
- Backend API: `FastAPI`, `Pydantic`
- Voice Worker: `Python`, `LiveKit Agents`
- Orchestration: `LangChain`, `LangGraph`
- Vector/RAG: `ChromaDB`, `langchain-text-splitters`, `pypdf`
- Providers: `Groq`, `Deepgram`, `AssemblyAI`, `ElevenLabs`, `Cartesia`

## Orchestrator Location
LangGraph orchestration lives in `backend/app/agent/`:
- `graph.py`
- `state.py`
- `prompts.py`
- `llm.py`
- `memory.py`

## Voice Pipeline Flow
1. Browser streams mic audio to LiveKit.
2. Worker streams audio to selected STT provider.
3. Final transcript enters LangGraph (`[AgentGraph] Received transcript`).
4. Graph retrieves document context and calls LangChain LLM for one final response.
5. Worker emits `assistant_complete` with response metadata.
6. Worker synthesizes and plays one full TTS response.

## Setup
### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Create `backend/.env` with required values:
- `LIVEKIT_WS_URL`
- `LIVEKIT_API_URL` (optional if same as websocket host)
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `GROQ_API_KEY`
- STT/TTS keys for selected providers:
  - `DEEPGRAM_API_KEY` or `ASSEMBLYAI_API_KEY`
  - `ELEVENLABS_API_KEY` or `CARTESIA_API_KEY`

Useful optional env vars:
- `GROQ_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `RAG_EMBEDDING_PROVIDER`
- `RAG_STORAGE_DIR`
- `RAG_TOP_K`
- `RAG_MAX_DISTANCE`
- `STT_FALLBACK_PROVIDER` (placeholder)
- `TTS_FALLBACK_PROVIDER` (placeholder)

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Optional:
- `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000/api`)
- `NEXT_PUBLIC_DEBUG_VOICE_LOGS=true` for verbose client logs

## Run Commands
- Backend API:
```bash
cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Worker:
```bash
cd backend && .venv\Scripts\activate && python -m app.worker dev
```
- Frontend:
```bash
cd frontend && npm run dev
```

## RAG Over Uploaded Documents
- Upload `.txt`/`.pdf` via UI panel or `POST /api/documents/upload`.
- Backend extracts text, chunks with LangChain splitter, embeds, and stores in Chroma.
- During response generation, LangGraph retrieves relevant chunks before LLM generation.
- If retrieval fails or no chunks match, conversation continues without document grounding.

## Session Memory
- Memory is scoped to each active voice session.
- Stores recent user/assistant turns and provides a lightweight summary.
- Improves follow-up handling (e.g., �explain that again�, �what did I ask earlier?�).

## Latency & Observability
- Event stream includes:
  - `user_transcript` with `stt_latency_ms`
  - `assistant_complete` with `llm_latency_ms` (and optional `tts_latency_ms`)
- Operational logs include:
  - `[AgentGraph] Received transcript`
  - `[LangChainLLM] Calling Groq model`
  - `[AgentGraph] Final response generated`
  - `[RAG] ...`

## Future Improvements
- Add automatic STT/TTS/LLM provider fallback routing.
- Add metrics endpoint/dashboard and long-session analytics.
- Add multi-session memory persistence options.
