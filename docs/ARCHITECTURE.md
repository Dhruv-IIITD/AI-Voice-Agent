# Runtime Architecture

## Active Voice Runtime Flow

```text
Browser Microphone
  -> LiveKit session
  -> STT provider
  -> LangGraph agent
       -> session memory load/update
       -> RAG retrieval (best-effort)
       -> tool decision + tool execution (best-effort)
       -> LangChain LLM response generation
  -> TTS provider (chunked playback)
  -> Browser audio response
```

## Notes
- LLM orchestration is centralized in `backend/app/agent/graph.py` and `backend/app/agent/llm.py`.
- RAG retrieval failures are non-fatal; conversation falls back to normal LLM response.
- Tool failures are non-fatal; assistant explains tool failure naturally.
- Worker streams `assistant_delta` immediately and sends `assistant_complete` when final text is ready.
- STT/TTS/provider errors are logged with clear messages and surfaced to the frontend when possible.
