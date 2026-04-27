import type {
  AgentSummary,
  HealthResponse,
  DocumentDeleteResponse,
  DocumentListResponse,
  DocumentSummary,
  DocumentUploadResponse,
  SessionCreateRequest,
  SessionResponse
} from "../types";

export interface MetricsResponse {
  total_latency_ms?: number;
  stt_latency_ms?: number;
  rag_retrieval_latency_ms?: number;
  tool_execution_latency_ms?: number;
  llm_latency_ms?: number;
  tts_latency_ms?: number;
  selected_stt_provider?: string;
  selected_tts_provider?: string;
  tools_called?: string[];
  retrieved_chunks_count?: number;
}

export class ApiRequestError extends Error {
  readonly status: number | null;
  readonly path: string;

  constructor(message: string, path: string, status?: number | null) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status ?? null;
    this.path = path;
  }
}

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

// helper function to make API requests
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const headers = new Headers(init?.headers ?? {});
  if (!isFormData && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers
    });
  } catch (caughtError) {
    const errorMessage =
      caughtError instanceof Error ? caughtError.message : "Unknown network error while reaching backend API.";
    throw new ApiRequestError(`Backend request failed (${path}): ${errorMessage}`, path);
  }

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as { detail?: string };
      throw new ApiRequestError(payload.detail || `Request failed with ${response.status}`, path, response.status);
    }
    const body = await response.text();
    throw new ApiRequestError(body || `Request failed with ${response.status}`, path, response.status);
  }

  return response.json() as Promise<T>;
}

// 1. fetch list of available agents from the backend
export function fetchAgents(): Promise<AgentSummary[]> {
  return request<AgentSummary[]>("/agents", { method: "GET" });
}

// 2. create a new voice session
export function createSession(payload: SessionCreateRequest): Promise<SessionResponse> {
  return request<SessionResponse>("/sessions", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const body = new FormData();
  body.append("file", file);

  const response = await request<DocumentUploadResponse>("/documents/upload", {
    method: "POST",
    body
  });
  return response.document;
}

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const response = await request<DocumentListResponse>("/documents", { method: "GET" });
  return response.documents;
}

export function deleteDocument(documentId: string): Promise<DocumentDeleteResponse> {
  return request<DocumentDeleteResponse>(`/documents/${documentId}`, {
    method: "DELETE"
  });
}

export function fetchBackendHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { method: "GET" });
}

export async function fetchBackendMetrics(): Promise<MetricsResponse | null> {
  const candidatePaths = ["/metrics/latest", "/metrics"];

  for (const path of candidatePaths) {
    try {
      return await request<MetricsResponse>(path, { method: "GET" });
    } catch (caughtError) {
      if (caughtError instanceof ApiRequestError && caughtError.status === 404) {
        continue;
      }
      throw caughtError;
    }
  }

  return null;
}
