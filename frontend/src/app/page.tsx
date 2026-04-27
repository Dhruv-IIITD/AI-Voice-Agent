"use client";

import Link from "next/link";

import { FeatureCard } from "@/components/common/feature-card";
import { BackendStatusBanner } from "@/components/status/backend-status-banner";
import { useVoicePlatform } from "@/features/voice/context/voice-platform-context";

import styles from "./dashboard.module.css";

const FEATURES = [
  {
    title: "Real-time voice conversation",
    description: "Talk to specialized AI agents in a live browser voice session through LiveKit transport."
  },
  {
    title: "RAG over uploaded documents",
    description: "Upload PDFs and text files, then ask grounded questions using retrieved document chunks."
  },
  {
    title: "Agent tools and session memory",
    description: "Inspect tool calls and memory-aware responses as the session evolves across multiple turns."
  },
  {
    title: "Latency observability",
    description: "Track STT, LLM, and TTS timing with a dedicated metrics view for performance inspection."
  }
];

const HOW_IT_WORKS_STEPS = [
  "Upload documents",
  "Choose an agent",
  "Start voice session",
  "Ask document-grounded questions",
  "Review transcript, tools, chunks, and metrics"
];

export default function DashboardPage() {
  const { backendStatus, backendMessage } = useVoicePlatform();

  return (
    <main className="pageShell">
      {(backendStatus === "preview" || backendStatus === "unavailable") && (
        <BackendStatusBanner message={backendMessage} status={backendStatus} />
      )}

      <header className="pageHeader">
        <p className="eyebrow">Portfolio Project</p>
        <h1 className="pageTitle">Real-Time Agentic Voice AI Platform</h1>
        <p className="pageSubtitle">
          Talk to AI agents over voice, ground answers in uploaded documents, and inspect tools, memory, and latency
          in real time.
        </p>
        <div className="actionRow">
          <Link className="primaryAction" href="/agent">
            Start Voice Agent
          </Link>
          <Link className="secondaryAction" href="/documents">
            Upload Documents
          </Link>
        </div>
      </header>

      <section className="sectionCard">
        <h2 className="sectionTitle">Platform Capabilities</h2>
        <p className="sectionSubtitle">A full-stack voice AI workflow built for real-time retrieval and observability.</p>
        <div className={styles.featureGrid}>
          {FEATURES.map((feature) => (
            <FeatureCard key={feature.title} description={feature.description} title={feature.title} />
          ))}
        </div>
      </section>

      <section className="sectionCard">
        <h2 className="sectionTitle">How It Works</h2>
        <div className={styles.howItWorks}>
          {HOW_IT_WORKS_STEPS.map((step, index) => (
            <article className={styles.step} key={step}>
              <span className={styles.stepIndex}>{index + 1}</span>
              <p className={styles.stepText}>{step}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
