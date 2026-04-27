import type { BackendConnectionStatus } from "@/features/voice/context/voice-platform-context";

import styles from "./backend-status-banner.module.css";

interface BackendStatusBannerProps {
  status: BackendConnectionStatus;
  message: string | null;
}

const TITLES: Record<BackendConnectionStatus, string> = {
  connected: "Backend Connected",
  unavailable: "Backend Unavailable",
  preview: "Frontend Preview Mode",
  checking: "Checking Backend"
};

const DEFAULT_MESSAGES: Record<BackendConnectionStatus, string> = {
  connected: "Live backend services are available for voice, RAG retrieval, memory, and observability.",
  unavailable:
    "Backend is unavailable. Start the FastAPI backend and LiveKit worker to use real voice, RAG, memory, and metrics features.",
  preview:
    "Backend is unavailable. Start the FastAPI backend and LiveKit worker to use real voice, RAG, memory, and metrics features.",
  checking: "Checking connectivity with backend services."
};

export function BackendStatusBanner({ status, message }: BackendStatusBannerProps) {
  return (
    <section className={`${styles.banner} ${styles[status]}`}>
      <p className={styles.title}>{TITLES[status]}</p>
      <p className={styles.text}>{message ?? DEFAULT_MESSAGES[status]}</p>
    </section>
  );
}
