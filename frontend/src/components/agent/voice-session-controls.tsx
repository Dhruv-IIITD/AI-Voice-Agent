import type { AssistantState, ConnectionState } from "@/features/voice/types";

import styles from "./voice-session-controls.module.css";

interface VoiceSessionControlsProps {
  connectionState: ConnectionState;
  assistantState: AssistantState;
  isConnected: boolean;
  isMuted: boolean;
  canConnect: boolean;
  onConnect: () => Promise<void>;
  onDisconnect: () => Promise<void>;
  onToggleMute: () => Promise<void>;
}

export function VoiceSessionControls({
  connectionState,
  assistantState,
  isConnected,
  isMuted,
  canConnect,
  onConnect,
  onDisconnect,
  onToggleMute
}: VoiceSessionControlsProps) {
  const title =
    connectionState === "connecting" ? "Connecting to voice session..." : isConnected ? "Voice session is live" : "Ready";
  const subtitle = isConnected
    ? `Assistant state: ${assistantState}`
    : "Choose an agent profile and start a real-time voice session.";

  return (
    <section className={styles.card}>
      <div>
        <h3 className={styles.title}>Voice Session Controls</h3>
        <p className={styles.subtitle}>
          <strong>{title}</strong> - {subtitle}
        </p>
      </div>

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
          End Voice Session
        </button>
      )}

      <button
        className={styles.secondaryButton}
        disabled={!isConnected}
        onClick={() => void onToggleMute()}
        type="button"
      >
        {isMuted ? "Unmute Microphone" : "Mute Microphone"}
      </button>
    </section>
  );
}
