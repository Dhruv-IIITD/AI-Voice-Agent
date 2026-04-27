import { API_BASE_URL, ApiRequestError } from "./api-client";

function isNetworkStyleError(message: string) {
  const normalized = message.toLowerCase();
  return (
    normalized.includes("failed to fetch") ||
    normalized.includes("networkerror") ||
    normalized.includes("backend request failed")
  );
}

export function toUserFriendlyBackendError(error: unknown, fallbackAction: string): string {
  if (typeof error === "string") {
    if (isNetworkStyleError(error)) {
      return `Backend is unavailable at ${API_BASE_URL}. Start the FastAPI API and LiveKit worker to use live voice, RAG, memory, and metrics.`;
    }
    return error;
  }

  if (error instanceof ApiRequestError) {
    if (error.status === 404) {
      return `${fallbackAction} is not available from the backend yet.`;
    }

    if (error.status === 503) {
      return "RAG storage is unavailable right now. Check vector DB and embedding configuration.";
    }

    if (isNetworkStyleError(error.message)) {
      return `Backend is unavailable at ${API_BASE_URL}. Start the FastAPI API and LiveKit worker to use live voice, RAG, memory, and metrics.`;
    }

    return error.message;
  }

  if (error instanceof Error) {
    if (isNetworkStyleError(error.message)) {
      return `Backend is unavailable at ${API_BASE_URL}. Start the FastAPI API and LiveKit worker to use live voice, RAG, memory, and metrics.`;
    }

    return error.message;
  }

  return fallbackAction;
}
