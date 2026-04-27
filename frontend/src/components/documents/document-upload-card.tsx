"use client";

import { useRef, useState, type DragEvent } from "react";

import styles from "./document-upload-card.module.css";

interface DocumentUploadCardProps {
  isUploading: boolean;
  onUpload: (file: File) => Promise<void>;
}

export function DocumentUploadCard({ isUploading, onUpload }: DocumentUploadCardProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  async function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file) {
      return;
    }
    await onUpload(file);
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    void handleFiles(event.dataTransfer.files);
  }

  return (
    <section className={styles.card}>
      <div>
        <h2 className={styles.title}>Knowledge Base Upload</h2>
        <p className={styles.subtitle}>Upload .txt or .pdf files to ground the voice agent.</p>
      </div>

      <div
        className={`${styles.dropZone} ${isDragging ? styles.dropZoneActive : ""}`}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className={styles.dropContent}>
          <p className={styles.dropText}>
            {isUploading ? "Uploading document..." : "Drag and drop a file here or choose a file manually."}
          </p>
          <button
            className={styles.pickerButton}
            disabled={isUploading}
            onClick={() => fileInputRef.current?.click()}
            type="button"
          >
            {isUploading ? "Uploading..." : "Choose File"}
          </button>
          <input
            ref={fileInputRef}
            accept=".txt,.pdf"
            className={styles.input}
            onChange={(event) => {
              void handleFiles(event.target.files);
              event.currentTarget.value = "";
            }}
            type="file"
          />
        </div>
      </div>
    </section>
  );
}
