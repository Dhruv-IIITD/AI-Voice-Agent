# AI Voice Agent

## Project Description
This project is a real-time, browser-based voice AI platform that supports multi-provider STT/TTS, LangGraph-based orchestration, RAG over uploaded documents, tool calling, session memory, and streaming voice responses.

## Problem It Solves
Most voice assistants either feel high-latency or have rigid pipelines. This system focuses on a practical developer architecture that keeps voice interactions responsive while supporting grounded document answers and agent workflows.

## Key Features
- Real-time voice sessions from browser microphone to spoken assistant reply.
- LangChain + LangGraph orchestration for structured backend response generation.
- RAG over uploaded `.txt` and `.pdf` documents with local Chroma vector storage.
- Session-scoped memory for follow-up and conversational continuity.
- Local/mock tool calling (`document search`, `conversation summary`, `session context`, `mock ticket creation`) plus existing demo agent tools.
- Streaming text deltas + incremental TTS playback for reduced perceived latency.
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
       -> Tool Selection/Execution (if relevant)
       -> LangChain Chat Model (OpenRouter)
  -> Streaming Assistant Text Events
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
- Providers: `OpenRouter`, `Deepgram`, `AssemblyAI`, `ElevenLabs`, `Cartesia`

## Orchestrator Location
LangGraph orchestration lives in `backend/app/agent/`:
- `graph.py`
- `state.py`
- `prompts.py`
- `llm.py`
- `memory.py`
- `tools/`

## Voice Pipeline Flow
1. Browser streams mic audio to LiveKit.
2. Worker streams audio to selected STT provider.
3. Final transcript enters LangGraph (`[AgentGraph] Received transcript`).
4. Graph loads session memory, runs retrieval/tool logic as needed, and calls LangChain LLM.
5. Text is streamed to frontend as `assistant_delta` events.
6. Worker synthesizes chunked TTS in parallel and plays audio immediately.
7. Final message and metadata are emitted as `assistant_complete`.

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
- `OPENROUTER_API_KEY`
- STT/TTS keys for selected providers:
  - `DEEPGRAM_API_KEY` or `ASSEMBLYAI_API_KEY`
  - `ELEVENLABS_API_KEY` or `CARTESIA_API_KEY`

Useful optional env vars:
- `OPENROUTER_MODEL`
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

## Tool Calling
- Tool selection happens in the LangGraph workflow.
- Current tools include:
  - `search_uploaded_docs(query)`
  - `summarize_conversation()`
  - `create_mock_ticket(title, description)`
  - `get_session_context()`
  - existing demo tools (`current_time`, `calculate_expression`, FAQ/order-status helpers)
- Tool calls are surfaced to frontend through `tool_call` events.

## Session Memory
- Memory is scoped to each active voice session.
- Stores recent user/assistant turns and maintains a rolling summary for longer chats.
- Improves follow-up handling (e.g., �explain that again�, �what did I ask earlier?�).

## Latency & Observability
- Event stream includes:
  - `user_transcript` with `stt_latency_ms`
  - `assistant_complete` with `llm_latency_ms` (and optional `tts_latency_ms`)
  - `tool_call` summaries
- Operational logs include:
  - `[AgentGraph] Received transcript`
  - `[LangChainLLM] Calling OpenRouter model`
  - `[AgentGraph] Final response generated`
  - `[Memory] ...`
  - `[ToolCall] ...`
  - `[RAG] ...`

## Future Improvements
- Add automatic STT/TTS/LLM provider fallback routing.
- Add richer tool planning with explicit model function-calling contracts.
- Add metrics endpoint/dashboard and long-session analytics.
- Add multi-session memory persistence options.
