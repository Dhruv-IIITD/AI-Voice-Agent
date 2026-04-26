# Testing Checklist

## 1) Setup Commands

### Backend API
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Worker
```bash
cd backend
.venv\Scripts\activate
python -m app.worker dev
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 2) Happy Path: Normal Voice Conversation
1. Open the frontend at `http://localhost:3000`.
2. Select an agent and providers.
3. Start a voice session and ask: “What can you help me with?”
4. Verify:
   - `user_transcript` appears in UI.
   - `assistant_delta` streams live text.
   - Assistant audio starts before generation fully completes.
   - Final response appears with `assistant_complete`.

## 3) Document Upload
1. Upload a `.txt` file.
2. Upload a `.pdf` file.
3. Verify both appear in the documents list with chunk counts.
4. Delete one document and verify it is removed.

## 4) RAG Query
1. Ask: “Summarize the uploaded document.”
2. Ask: “What technologies are mentioned in it?”
3. Verify:
   - Tool/RAG context appears in logs.
   - Retrieved chunks are visible in Session Insights.
   - Response references uploaded documents naturally.

## 5) Follow-Up Memory
1. Ask a question with a detailed answer.
2. Follow with: “Explain that in simpler words.”
3. Ask: “What did I ask you before this?”
4. Verify memory summary is updated and follow-up answers are contextual.

## 6) Tool Calling
Use these phrases and verify `tool_call` events in UI/logs:
1. “Summarize our conversation so far.”
2. “Create a ticket saying the voice agent latency is high.”
3. “Search my uploaded document for backend technologies.”

## 7) Mock Ticket Creation
1. Ask: “Create a ticket saying the voice agent latency is high.”
2. Verify tool result includes ticket id/status.
3. Verify `backend/.agent_store/mock_tickets.json` contains the new ticket.

## 8) Latency Metrics
1. Run a normal query.
2. Verify transcript entries display `STT` and `LLM` latency values when available.
3. Confirm worker logs include response-timing information.

## 9) Error Handling: Missing Keys / Provider Issues
1. Stop services.
2. Remove one provider key (example: `DEEPGRAM_API_KEY`) from `backend/.env`.
3. Restart backend and try creating a session with that provider.
4. Verify API returns a clear configuration error.
5. Re-add key and repeat for a TTS provider key.

## 10) Error Handling: Upload Edge Cases
1. Try uploading an unsupported extension (example: `.docx`).
2. Try uploading an empty file.
3. Try uploading a PDF with no extractable text.
4. Verify API returns clear messages and backend remains stable.
