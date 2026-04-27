"use client";

import { DocumentUploadCard } from "@/components/documents/document-upload-card";
import { DocumentsList } from "@/components/documents/documents-list";
import { BackendStatusBanner } from "@/components/status/backend-status-banner";
import { useVoicePlatform } from "@/features/voice/context/voice-platform-context";
import { useDocuments } from "@/features/voice/hooks/use-documents";

import styles from "./documents-page.module.css";

export default function DocumentsPage() {
  const { backendStatus, backendMessage } = useVoicePlatform();
  const { documents, isLoading, isUploading, error, uploadDocumentFile, deleteDocumentById } = useDocuments();

  return (
    <main className="pageShell">
      {(backendStatus === "preview" || backendStatus === "unavailable") && (
        <BackendStatusBanner message={backendMessage} status={backendStatus} />
      )}

      <header className="pageHeader">
        <p className="eyebrow">Knowledge Base</p>
        <h1 className="pageTitle">RAG Documents</h1>
        <p className="pageSubtitle">
          Upload knowledge files once, then ask the voice agent grounded questions against your personal document
          corpus.
        </p>
      </header>

      <section className={styles.layout}>
        <DocumentUploadCard isUploading={isUploading} onUpload={uploadDocumentFile} />
        {error ? <p className={styles.errorCard}>{error}</p> : null}
        <DocumentsList documents={documents} isLoading={isLoading} onDelete={deleteDocumentById} />
      </section>

      <section className="sectionCard">
        <h2 className="sectionTitle">Example Use Cases</h2>
        <div className={styles.useCases}>
          <p className={styles.useCaseItem}>Upload resume {"->"} run mock interview</p>
          <p className={styles.useCaseItem}>Upload README {"->"} explain project architecture</p>
          <p className={styles.useCaseItem}>Upload notes {"->"} ask tutor-style questions</p>
        </div>
      </section>
    </main>
  );
}
