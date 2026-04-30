# Backend Flow Documentation

## 1. High-Level Flow

Current backend flow in this codebase:

User speech  
-> STT creates text  
-> backend receives `user_text`  
-> `AIVoiceWorker.generate_and_stream_response(user_text)`  
-> `ConversationSession.reply(user_text)`  
-> `VoiceAgentGraph.run(...)`  
-> RAG retrieves document chunks  
-> prompt is built  
-> LLM generates final answer  
-> backend sends `assistant_complete` event  
-> TTS converts final answer to audio  
-> audio is played  
-> assistant returns to listening state

ASCII diagram:

```text
Browser Mic
   |
   v
LiveKit audio track
   |
   v
STT provider (Deepgram/AssemblyAI) -> TranscriptEvent(text, is_final)
   |
   v
AIVoiceWorker.handle_transcript_stream()
   |
   v
AIVoiceWorker.generate_and_stream_response(user_text)
   |
   v
ConversationSession.reply(user_text)
   |
   v
VoiceAgentGraph.run(...)
   |         \
   |          -> retrieve_context -> retrieve_serialized_chunks(query)
   |                                  -> Chroma query -> chunks
   |
   -> generate_response -> build_prompt(...) -> generate_response_text(...)
   |
   -> update_memory -> SessionMemory.summarize_conversation()
   |
   v
publish_voice_event(type="assistant_complete", text, retrieved_chunks, memory_summary)
   |
   v
text_to_speech.synthesize(final_text)
   |
   v
tts_audio_player.play(audio.audio)
   |
   v
assistant_state = "listening"
```

## 2. Important Files and Functions

### `backend/app/worker.py`
- `AIVoiceWorker.handle_transcript_stream(self) -> None`
- Purpose: consumes STT events and triggers response generation only on final transcript.
- Receives: `TranscriptEvent` from `self.speech_to_text.events()`.
- Calls next: `publish_voice_event(... user_transcript ...)`, then `self.generate_and_stream_response(final_text)`.
- Produces: frontend transcript events and one backend turn per final user utterance.

- `AIVoiceWorker.generate_and_stream_response(self, user_text: str) -> None`
- Purpose: orchestrates one full backend turn (LLM/RAG + assistant_complete + TTS playback).
- Receives: `user_text` (final STT text).
- Calls next: `ConversationSession.reply(user_text)`, `publish_voice_event(type="assistant_complete", ...)`, `self.text_to_speech.synthesize(final_text)`, `self.tts_audio_player.play(audio.audio)`.
- Produces: `assistant_complete` event, audio playback, assistant state transitions.

### `backend/app/runtime/conversation.py`
- `ConversationSession.reply(self, user_text: str) -> ConversationReply`
- Purpose: manages turn-level history, invokes LangGraph pipeline, returns finalized response payload.
- Receives: user utterance text.
- Calls next: `VoiceAgentGraph.run(user_text, session_memory, history)`.
- Returns: `ConversationReply(text, retrieved_chunks, memory_summary)`.

### `backend/app/agent/graph.py`
- `VoiceAgentGraph.__init__(agent: AgentDefinition)`
- Purpose: builds LangGraph workflow with `StateGraph(AgentState)`.
- Nodes added: `"retrieve_context"`, `"generate_response"`, `"update_memory"`.
- Edges: `START -> retrieve_context -> generate_response -> update_memory -> END`.

- `VoiceAgentGraph.run(...) -> AgentGraphResult`
- Purpose: creates initial graph state and runs graph asynchronously.
- Receives: `user_text`, `session_memory`, `history`.
- Calls next: `self._graph.ainvoke(initial_state)`.
- Returns: `AgentGraphResult(response_text, retrieved_chunks, memory_summary)`.

- `VoiceAgentGraph._retrieve_context(state: AgentState) -> AgentState`
- Purpose: RAG retrieval node.
- Receives: graph state (`user_text`).
- Calls next: `retrieve_serialized_chunks(user_text)`.
- Returns: `{"retrieved_chunks": [...], "rag_context": "..."}`

- `VoiceAgentGraph._generate_response(state: AgentState) -> AgentState`
- Purpose: prompt + LLM node.
- Receives: `rag_context`, `user_text`, `history`.
- Calls next: `build_prompt(...)`, `generate_response_text(system_prompt, history)`.
- Returns: `{"response_text": response_text}`.

- `VoiceAgentGraph._update_memory(state: AgentState) -> AgentState`
- Purpose: memory update node.
- Receives: `user_text`, `response_text`, `session_memory`.
- Calls next: `session_memory.add_user_turn(...)`, `session_memory.add_assistant_turn(...)`, `session_memory.summarize_conversation()`.
- Returns: `{"memory_summary": ...}`.

### `backend/app/rag/retriever.py`
- `retrieve_serialized_chunks(query: str) -> list[dict[str, object]]`
- Purpose: public RAG retrieval function used by graph.
- Receives: query text.
- Calls next: `get_document_retriever().retrieve(query)` and `serialize_chunk(...)`.
- Returns: serialized chunks list with `document_id`, `filename`, `chunk_index`, `snippet`, `content`, `distance`.

### `backend/app/agent/prompts.py`
- `build_prompt(agent_system_prompt, rag_context, user_text) -> str`
- Purpose: builds system prompt string used by the LLM call.
- Receives: base agent prompt, optional RAG context, current user request.
- Calls next: consumed by `generate_response_text(...)`.
- Returns: final system prompt text.

Note on naming:
- `build_orchestrator_prompt(...)` is not present in the current codebase.
- The current prompt builder used in flow is `build_prompt(...)`.

### `backend/app/agent/llm.py`
- `generate_response_text(system_prompt, history) -> str`
- Purpose: executes one async LLM call and applies timeout/fallback logic.
- Receives: prepared `system_prompt` and chat `history`.
- Calls next: `get_chat_model()` -> `ChatGroq(...).ainvoke(messages)`.
- Returns: final assistant text (or fallback text if timeout/error/empty).

### `backend/app/providers/tts/base.py` and `backend/app/runtime/audio.py`
- `text_to_speech.synthesize(final_text)` (provider implementation)
- Purpose: convert final text into PCM bytes.
- Receives: final assistant text.
- Calls next: external TTS API (`ElevenLabsTTSClient` or `CartesiaTTSClient`).
- Returns: `SynthesizedAudio(audio: bytes, sample_rate, num_channels)`.

- `tts_audio_player.play(audio.audio)`
- Purpose: splits PCM bytes into frames and publishes them to LiveKit audio source.
- Receives: raw PCM bytes.
- Calls next: `rtc.AudioFrame.create(...)` + `self._source.capture_frame(frame)`.
- Produces: audible assistant speech in the room.

## 3. Exact Call Flow

1. STT provider emits final text as `TranscriptEvent` in `BaseStreamingSTT.events()`.
2. `AIVoiceWorker.handle_transcript_stream()` receives the final event and extracts `final_text`.
3. It publishes `user_transcript` and calls `AIVoiceWorker.generate_and_stream_response(final_text)`.
4. `generate_and_stream_response(...)` sets assistant state to `thinking`.
5. It calls `ConversationSession.reply(user_text)`.
6. `ConversationSession.reply()` appends the user turn into `self._history` and trims to last 14 messages.
7. It calls `VoiceAgentGraph.run(user_text, session_memory, history)`.
8. `VoiceAgentGraph.run()` builds initial `AgentState` and invokes LangGraph with `self._graph.ainvoke(...)`.
9. Node `retrieve_context` runs `VoiceAgentGraph._retrieve_context()`.
10. `_retrieve_context()` calls `retrieve_serialized_chunks(user_text)`.
11. `retrieve_serialized_chunks()` calls `DocumentRetriever.retrieve()` -> `RagVectorStore.query(...)` -> serializes chunks.
12. `_retrieve_context()` builds `rag_context` from retrieved chunk `filename`, `chunk_index`, and `content`.
13. Node `generate_response` runs `VoiceAgentGraph._generate_response()`.
14. `_generate_response()` calls `build_prompt(...)`.
15. `_generate_response()` calls `generate_response_text(system_prompt, history)`.
16. `generate_response_text()` calls `ChatGroq.ainvoke(messages)` and returns final text (or fallback).
17. Node `update_memory` runs `VoiceAgentGraph._update_memory()`, saves turns, creates `memory_summary`.
18. `VoiceAgentGraph.run()` returns `AgentGraphResult(response_text, retrieved_chunks, memory_summary)`.
19. `ConversationSession.reply()` appends assistant message to history, then returns `ConversationReply`.
20. `generate_and_stream_response()` publishes `assistant_complete` with `text`, `llm_latency_ms`, `retrieved_chunks`, `memory_summary`.
21. It changes state to `speaking`.
22. It calls `text_to_speech.synthesize(final_text)`.
23. It calls `tts_audio_player.play(audio.audio)`.
24. It sets assistant state back to `listening`.

## 4. LangGraph and RAG Flow

- `StateGraph(AgentState)` is created in `backend/app/agent/graph.py` inside `VoiceAgentGraph.__init__`.
- Added nodes:
  - `"retrieve_context"` -> `self._retrieve_context`
  - `"generate_response"` -> `self._generate_response`
  - `"update_memory"` -> `self._update_memory`
- Connected edges:
  - `START -> retrieve_context`
  - `retrieve_context -> generate_response`
  - `generate_response -> update_memory`
  - `update_memory -> END`

What each node does:
- `retrieve_context`: runs retrieval and constructs `rag_context` text block.
- `generate_response`: builds prompt and does one LLM generation call.
- `update_memory`: stores turn data in `SessionMemory` and computes summary.

How chunks are retrieved:
- `retrieve_serialized_chunks(query)` in `backend/app/rag/retriever.py` calls `DocumentRetriever.retrieve(query)`.
- `DocumentRetriever.retrieve` queries Chroma via `RagVectorStore.query(...)`.
- `RagVectorStore.query` reads from collection `voice_documents` in `.rag_store`.
- Results are filtered by distance (`DEFAULT_MAX_DISTANCE = 1.2`) and top-k (`DEFAULT_TOP_K = 4`).

How `rag_context` is created:
- `VoiceAgentGraph._retrieve_context` joins chunks as:
  - `[filename | chunk X]`
  - full `content`
- Joined with double newlines into one string.

How RAG context reaches LLM prompt:
- `_generate_response` passes `rag_context` into `build_prompt(...)`.
- `build_prompt` conditionally inserts an `Uploaded document context:` block.

How retrieved chunks reach frontend:
- `VoiceAgentGraph.run` returns `retrieved_chunks`.
- `ConversationSession.reply` includes them in `ConversationReply`.
- `AIVoiceWorker.generate_and_stream_response` sends them in `assistant_complete.retrieved_chunks`.
- Frontend `useVoiceSession.handleVoiceEvent` stores them via `setRetrievedChunks(...)`.

## 5. Prompt and LLM Call

- System prompt source:
  - Agent base prompt comes from `AgentDefinition.system_prompt` in `backend/app/agents/catalog.py`.
  - That base prompt is passed to `build_prompt(...)` in `backend/app/agent/prompts.py`.

- How history and RAG context are included:
  - Conversation history (`self._history`) is passed into `VoiceAgentGraph.run(...)`.
  - `build_prompt(...)` includes `rag_context` and `Current user request`.
  - `generate_response_text(...)` converts history into LangChain messages:
    - `SystemMessage(system_prompt)`
    - `HumanMessage` / `AIMessage` from history.

- Where `generate_response_text(...)` is called:
  - `VoiceAgentGraph._generate_response` in `backend/app/agent/graph.py`.

- Provider/model used (current code):
  - `generate_response_text` uses `ChatGroq` (`langchain_groq`) in `backend/app/agent/llm.py`.
  - Model is `GROQ_MODEL` env var, default `"llama-3.1-8b-instant"`.
  - Temperature from `LLM_TEMPERATURE` (default `0.2`).
  - Timeout from `LLM_TIMEOUT_SECONDS` (default `35`).

- What LLM returns:
  - `response.content` is normalized by `_content_to_text(...)`, stripped, and returned as plain string.
  - On timeout/error/empty, fallback text is returned.

## 6. Memory / History

- Where history is stored:
  - Turn history: `ConversationSession._history` in `backend/app/runtime/conversation.py`.
  - Session memory: `SessionMemory._turns` in `backend/app/agent/memory.py`.

- How user messages are added:
  - `ConversationSession.reply()` appends `{"role": "user", "content": user_text}`.
  - `VoiceAgentGraph._update_memory()` also calls `session_memory.add_user_turn(user_text)`.

- How assistant messages are added:
  - After graph result, `ConversationSession.reply()` appends `{"role": "assistant", "content": final_text}`.
  - `VoiceAgentGraph._update_memory()` calls `session_memory.add_assistant_turn(response_text)`.

- How many messages are kept:
  - Conversation history keeps last `14` messages (`_max_history_messages = 14`).
  - SessionMemory keeps up to `max_recent_turns` (default `16`, min `4`).

- How `memory_summary` is created:
  - `SessionMemory.summarize_conversation()` takes last 8 memory turns.
  - Each line format: `Role: text[:160]`.
  - Lines are joined into one summary string.
  - Returned by `VoiceAgentGraph._update_memory()` and included in `assistant_complete`.

## 7. Frontend Events and TTS

Events published to frontend (via `publish_voice_event` topic `voice-event`):
- `session_ready`
- `assistant_state`
- `user_transcript`
- `assistant_complete`
- `assistant_warning`

Current `assistant_complete` payload from backend:
- `type`
- `text`
- `llm_latency_ms`
- `retrieved_chunks`
- `memory_summary`

When TTS starts:
- In `generate_and_stream_response`, TTS starts only after `assistant_complete` is published and state is changed to `speaking`.

How `text_to_speech.synthesize(final_text)` works in flow:
- Selected provider is created in `build_tts_provider(...)` (`elevenlabs` or `cartesia`).
- `synthesize` sends text to provider API and returns `SynthesizedAudio` with PCM bytes.

How `tts_audio_player.play(audio.audio)` is used:
- `AudioTrackPlayer.play(...)` slices PCM bytes into fixed-size frames and pushes each frame to LiveKit audio source.
- Remote client receives assistant audio track and plays it.

Assistant state transitions:
- Initial/session-ready: `listening`
- User final transcript received: `thinking`
- After `assistant_complete` and before playback: `speaking`
- After playback success or failure: `listening`
- STT runtime failure path: `disconnected`

Note:
- Frontend type also supports `assistant_delta` and `tool_call`, but current `AIVoiceWorker` flow does not emit these events.

## 8. Failure Scenarios

| Scenario | Current behavior in code |
|---|---|
| RAG retrieval fails | `VoiceAgentGraph._retrieve_context` catches exception, logs it, and returns empty `retrieved_chunks` + empty `rag_context`; pipeline continues. |
| No chunks found | `retrieve_serialized_chunks` returns `[]`; `build_prompt` skips uploaded-context block; LLM answers without RAG context. |
| LLM generation fails | `generate_response_text` catches errors/timeouts and returns fallback text. If graph run itself fails, `ConversationSession.reply` catches and falls back. |
| Empty response generated | `generate_response_text` returns fallback if empty; `ConversationSession.reply` also applies fallback; worker has extra fallback `"I did not generate a response."`. |
| TTS synthesis fails | Exception in `text_to_speech.synthesize` is caught; backend sends `assistant_warning`; state returns to `listening`; no audio playback. |
| TTS playback fails | Exception in `tts_audio_player.play` is caught; backend sends `assistant_warning`; finally returns to `listening`. |

