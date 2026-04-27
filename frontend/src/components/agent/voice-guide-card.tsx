import styles from "./voice-guide-card.module.css";

export function VoiceGuideCard() {
  return (
    <section className={styles.card}>
      <h3 className={styles.title}>Try Asking</h3>
      <ul className={styles.list}>
        <li className={styles.item}>Summarize my uploaded document.</li>
        <li className={styles.item}>Explain this project architecture.</li>
        <li className={styles.item}>Prepare interview questions from my resume.</li>
      </ul>
    </section>
  );
}
