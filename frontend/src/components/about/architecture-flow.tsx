import styles from "./architecture-flow.module.css";

const FLOW_STEPS = [
  "Browser microphone",
  "LiveKit session",
  "STT provider",
  "LangGraph agent",
  "Session memory",
  "RAG retrieval / tools",
  "LangChain LLM",
  "TTS provider",
  "Browser audio"
];

export function ArchitectureFlow() {
  return (
    <section className={styles.shell}>
      <div className={styles.flow}>
        {FLOW_STEPS.map((step, index) => (
          <div key={step}>
            <article className={styles.step}>
              <span className={styles.index}>{index + 1}</span>
              <p className={styles.label}>{step}</p>
            </article>
            {index < FLOW_STEPS.length - 1 ? <p className={styles.arrow}>{"->"}</p> : null}
          </div>
        ))}
      </div>
    </section>
  );
}
