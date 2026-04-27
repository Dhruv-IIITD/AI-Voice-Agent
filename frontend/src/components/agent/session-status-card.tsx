import styles from "./session-status-card.module.css";

interface SessionStatusCardProps {
  backendStatus: string;
  voiceStatus: string;
  selectedSttProvider: string;
  selectedTtsProvider: string;
  selectedAgentName: string;
}

export function SessionStatusCard({
  backendStatus,
  voiceStatus,
  selectedSttProvider,
  selectedTtsProvider,
  selectedAgentName
}: SessionStatusCardProps) {
  return (
    <section className={styles.card}>
      <h3 className={styles.title}>Current Session Status</h3>
      <div className={styles.rows}>
        <div className={styles.row}>
          <span className={styles.label}>Backend</span>
          <span className={styles.value}>{backendStatus}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>Voice Session</span>
          <span className={styles.value}>{voiceStatus}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>STT Provider</span>
          <span className={styles.value}>{selectedSttProvider}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>TTS Provider</span>
          <span className={styles.value}>{selectedTtsProvider}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>Selected Agent</span>
          <span className={styles.value}>{selectedAgentName}</span>
        </div>
      </div>
    </section>
  );
}
