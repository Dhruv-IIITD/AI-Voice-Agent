import type { AssistantState, ConnectionState } from "../types";

import styles from "./voice-workspace.module.css";

interface SessionControlsProps {
  connectionState: ConnectionState;
  assistantState: AssistantState;
  isConnected: boolean;
  isMuted: boolean;
  activeSpeakers: number;
  canConnect: boolean;
  onConnect: () => Promise<void>;
  onDisconnect: () => Promise<void>;
  onToggleMute: () => Promise<void>;
}

const ASSISTANT_LABELS: Record<AssistantState, string> = {
  idle: "Idle",
  listening: "Listening",
  thinking: "Processing",
  speaking: "Speaking",
  disconnected: "Disconnected"
};

export function SessionControls({
  connectionState,
  assistantState,
  isConnected,
  isMuted,
  activeSpeakers,
  canConnect,
  onConnect,
  onDisconnect,
  onToggleMute
}: SessionControlsProps) {
  const sessionTitle =
    connectionState === "connecting" ? "Connecting..." : isConnected ? "Session live" : "Ready to connect";
  const stateClassName = isConnected
    ? styles.sessionStateLive
    : connectionState === "connecting"
      ? styles.sessionStateBusy
      : connectionState === "error"
        ? styles.sessionStateError
        : styles.sessionStateIdle;
  const helperText = isConnected
    ? `${activeSpeakers} active speaker${activeSpeakers === 1 ? "" : "s"}`
    : "Select an agent, then start the session.";

  return (
    <section className={styles.sessionCard}>
      <div className={styles.sessionCardHeader}>
        <div>
          <span className={styles.sectionEyebrow}>Session</span>
          <strong>{sessionTitle}</strong>
        </div>
        <span className={`${styles.sessionStatePill} ${stateClassName}`}>{ASSISTANT_LABELS[assistantState]}</span>
      </div>

      <p className={styles.sessionCardMeta}>{helperText}</p>

      {!isConnected ? (
        <button
          className={styles.primaryButton}
          disabled={!canConnect || connectionState === "connecting"}
          onClick={() => void onConnect()}
          type="button"
        >
          {connectionState === "connecting" ? "Connecting..." : "Start Voice Session"}
        </button>
      ) : (
        <button className={styles.dangerButton} onClick={() => void onDisconnect()} type="button">
          End Session
        </button>
      )}

      <div className={styles.sessionButtonRow}>
        <button
          className={styles.secondaryButton}
          disabled={!isConnected}
          onClick={() => void onToggleMute()}
          type="button"
        >
          {isMuted ? "Unmute Mic" : "Mute Mic"}
        </button>
      </div>
    </section>
  );
}
