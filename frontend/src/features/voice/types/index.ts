export type SttProvider = "deepgram" | "assemblyai";
export type TtsProvider = "elevenlabs" | "cartesia";
export type ConnectionState = "idle" | "connecting" | "connected" | "error";
export type AssistantState = "idle" | "listening" | "thinking" | "speaking" | "disconnected";

export interface AgentSummary {
  id:string;
   name:string; // agent name
  description:string;
  system_prompt_preview:string;
    tool_names:string[];
  accent_color:string;
  stt_options:SttProvider[];
  tts_options:TtsProvider[];
}

export interface SessionCreateRequest {
  agent_id:string;
    display_name:string;
  stt_provider?:SttProvider; // maybe keep this optional
  tts_provider?:TtsProvider;
}

export interface SessionResponse {
  session_id:string;
   livekit_url:string;
  room_name:string;
    participant_identity:string;
  participant_name:string;
  token:string; // todo check if need to hide this
  selected_stt_provider:SttProvider;
  selected_tts_provider:TtsProvider;
  agent:AgentSummary;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface DocumentSummary {
  document_id: string;
  filename: string;
  chunk_count: number;
  uploaded_at: string;
}

export interface DocumentUploadResponse {
  document: DocumentSummary;
}

export interface DocumentListResponse {
  documents: DocumentSummary[];
}

export interface DocumentDeleteResponse {
  document_id: string;
  deleted: boolean;
}

export interface TranscriptEntry {
  id: string;
  role: "user" | "assistant" | "tool";
  text: string;
  isFinal: boolean;
  provider?: string;
  stt_latency_ms?: number;
  llm_latency_ms?: number;
  tts_latency_ms?: number;
}

export interface RetrievedChunk {
  document_id: string;
  filename: string;
  chunk_index: number;
  snippet: string;
  content: string;
  distance?: number;
}

export interface ToolCallEntry {
  name: string;
  arguments: Record<string, unknown>;
  resultSummary?: string;
  createdAt: string;
}

export type VoiceWorkerEvent =
  | {
      type: "session_ready";
      agentId: string;
      agentName: string;
      roomName: string;
    }
  | {
      type: "assistant_state";
      state: AssistantState;
    }
  | {
      type: "user_transcript";
      text: string;
      final: boolean;
      provider: string;
      stt_latency_ms?: number;
    }
  | {
      type: "assistant_delta";
      delta: string;
    }
  | {
      type: "assistant_complete";
      text: string;
      llm_latency_ms?: number;
      tts_latency_ms?: number;
      retrieved_chunks?: RetrievedChunk[];
      memory_summary?: string;
    }
  | {
      type: "assistant_warning";
      message: string;
    }
  | {
      type: "tool_call";
      toolName: string;
      arguments: Record<string, unknown>;
      resultSummary?: string;
    };
