import type { RetrievedChunk, SessionResponse, ToolCallEntry, TranscriptEntry } from "../types";

export interface SessionMetricsSnapshot {
  totalLatencyMs: number | null;
  sttLatencyMs: number | null;
  ragRetrievalLatencyMs: number | null;
  toolExecutionLatencyMs: number | null;
  llmLatencyMs: number | null;
  ttsLatencyMs: number | null;
  selectedSttProvider: string | null;
  selectedTtsProvider: string | null;
  toolsCalled: string[];
  retrievedChunksCount: number;
}

function getLastFinalTranscript(
  transcripts: TranscriptEntry[],
  role: TranscriptEntry["role"]
): TranscriptEntry | undefined {
  return [...transcripts].reverse().find((entry) => entry.role === role && entry.isFinal);
}

export function buildSessionMetricsSnapshot(params: {
  transcripts: TranscriptEntry[];
  session: SessionResponse | null;
  toolCalls: ToolCallEntry[];
  retrievedChunks: RetrievedChunk[];
}): SessionMetricsSnapshot {
  const { transcripts, session, toolCalls, retrievedChunks } = params;
  const latestUser = getLastFinalTranscript(transcripts, "user");
  const latestAssistant = getLastFinalTranscript(transcripts, "assistant");

  const sttLatencyMs = latestUser?.stt_latency_ms ?? null;
  const llmLatencyMs = latestAssistant?.llm_latency_ms ?? null;
  const ttsLatencyMs = latestAssistant?.tts_latency_ms ?? null;

  const components = [sttLatencyMs, llmLatencyMs, ttsLatencyMs].filter(
    (value): value is number => typeof value === "number"
  );
  const totalLatencyMs = components.length > 0 ? components.reduce((sum, value) => sum + value, 0) : null;

  return {
    totalLatencyMs,
    sttLatencyMs,
    ragRetrievalLatencyMs: null,
    toolExecutionLatencyMs: null,
    llmLatencyMs,
    ttsLatencyMs,
    selectedSttProvider: session?.selected_stt_provider ?? null,
    selectedTtsProvider: session?.selected_tts_provider ?? null,
    toolsCalled: Array.from(new Set(toolCalls.map((call) => call.name))).slice(-8),
    retrievedChunksCount: retrievedChunks.length
  };
}
