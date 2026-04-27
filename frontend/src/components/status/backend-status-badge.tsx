import type { BackendConnectionStatus } from "@/features/voice/context/voice-platform-context";

import styles from "./backend-status-badge.module.css";

interface BackendStatusBadgeProps {
  status: BackendConnectionStatus;
}

const STATUS_LABELS: Record<BackendConnectionStatus, string> = {
  connected: "Connected",
  unavailable: "Unavailable",
  preview: "Frontend Preview Mode",
  checking: "Checking"
};

export function BackendStatusBadge({ status }: BackendStatusBadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[status]}`}>
      <span className={styles.dot} />
      {STATUS_LABELS[status]}
    </span>
  );
}
