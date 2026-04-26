import type {
  AgentSummary,
  DocumentDeleteResponse,
  DocumentListResponse,
  DocumentSummary,
  DocumentUploadResponse,
  SessionCreateRequest,
  SessionResponse
} from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

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
    throw new Error(`Backend request failed (${path}): ${errorMessage}`);
  }

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as { detail?: string };
      throw new Error(payload.detail || `Request failed with ${response.status}`);
    }
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
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
