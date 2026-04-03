import type { AgentSummary, SessionCreateRequest, SessionResponse } from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function fetchAgents(): Promise<AgentSummary[]> {
  return request<AgentSummary[]>("/agents", { method: "GET" });
}

export function createSession(payload: SessionCreateRequest): Promise<SessionResponse> {
  return request<SessionResponse>("/sessions", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

