import type { AssistantState, ConnectionState } from "../types";

import styles from "./voice-workspace.module.css";

interface StatusBadgeProps {
  label: string;
  tone: AssistantState | ConnectionState;
}

const LABELS: Record<string, string> = {
  idle: "Idle",
  connecting: "Connecting",
  connected: "Connected",
  error: "Error",
  listening: "Listening",
  thinking: "Thinking",
  speaking: "Speaking",
  disconnected: "Disconnected"
};

const TONE_CLASS: Record<string, string> = {
  idle: styles.statusIdle,
  connecting: styles.statusConnecting,
  connected: styles.statusConnected,
  error: styles.statusError,
  listening: styles.statusListening,
  thinking: styles.statusThinking,
  speaking: styles.statusSpeaking,
  disconnected: styles.statusDisconnected
};

export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return (
    <div className={`${styles.statusBadge} ${TONE_CLASS[tone]}`}>
      <span className={styles.statusBadgeLabel}>{label}</span>
      <span className={styles.statusBadgeValue}>
        <span className={styles.statusDot} />
        {LABELS[tone]}
      </span>
    </div>
  );
}
