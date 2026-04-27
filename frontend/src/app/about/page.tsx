"use client";

import { ArchitectureFlow } from "@/components/about/architecture-flow";
import { BackendStatusBanner } from "@/components/status/backend-status-banner";
import { useVoicePlatform } from "@/features/voice/context/voice-platform-context";

import styles from "./about-page.module.css";

const STACK = [
  "Next.js",
  "FastAPI",
  "LiveKit",
  "LangChain",
  "LangGraph",
  "Vector DB / RAG",
  "Deepgram / AssemblyAI",
  "ElevenLabs / Cartesia"
];

export default function AboutPage() {
  const { backendStatus, backendMessage } = useVoicePlatform();

  return (
    <main className="pageShell">
      {(backendStatus === "preview" || backendStatus === "unavailable") && (
        <BackendStatusBanner message={backendMessage} status={backendStatus} />
      )}

      <header className="pageHeader">
        <p className="eyebrow">Architecture</p>
        <h1 className="pageTitle">About This Platform</h1>
        <p className="pageSubtitle">
          A recruiter-friendly breakdown of how this voice AI platform works and why it is different from a normal
          chatbot demo.
        </p>
      </header>

      <section className={`sectionCard ${styles.layout}`}>
        <h2 className="sectionTitle">What This Project Is</h2>
        <p className={styles.textBlock}>
          This project is a real-time, browser-based agentic voice platform. Users speak to specialized agents,
          retrieve context from uploaded documents, and get grounded spoken answers while observing transcript, tool
          calls, memory summary, and latency behavior.
        </p>
      </section>

      <section className={`sectionCard ${styles.layout}`}>
        <h2 className="sectionTitle">Why It Is Different From a Basic Chatbot</h2>
        <p className={styles.textBlock}>
          A normal chatbot usually focuses on typed text and static responses. This platform adds live voice transport,
          provider-swappable STT and TTS, retrieval-grounded reasoning over uploaded files, memory-aware dialogue, and
          observability for latency and tool activity.
        </p>
      </section>

      <section className={`sectionCard ${styles.layout}`}>
        <h2 className="sectionTitle">Architecture Flow</h2>
        <ArchitectureFlow />
      </section>

      <section className={`sectionCard ${styles.layout}`}>
        <h2 className="sectionTitle">Tech Stack</h2>
        <div className={styles.stackGrid}>
          {STACK.map((item) => (
            <p className={styles.stackItem} key={item}>
              {item}
            </p>
          ))}
        </div>
      </section>
    </main>
  );
}
