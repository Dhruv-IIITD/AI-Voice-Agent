import { EmptyState } from "@/components/common/empty-state";
import type { DocumentSummary } from "@/features/voice/types";

import styles from "./documents-list.module.css";

interface DocumentsListProps {
  documents: DocumentSummary[];
  isLoading: boolean;
  onDelete: (documentId: string) => Promise<void>;
}

export function DocumentsList({ documents, isLoading, onDelete }: DocumentsListProps) {
  return (
    <section className={styles.wrapper}>
      <header className={styles.header}>
        <h2 className={styles.title}>Uploaded Documents</h2>
        <span className={styles.count}>{documents.length} files</span>
      </header>

      {isLoading ? (
        <EmptyState title="Loading documents..." description="Fetching your knowledge base files from the backend." />
      ) : null}

      {!isLoading && documents.length === 0 ? (
        <EmptyState
          title="No documents uploaded yet."
          description="Upload a resume, project README, notes, or product FAQ to let the voice agent answer using your knowledge base."
        />
      ) : null}

      {!isLoading && documents.length > 0 ? (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Document ID</th>
                <th>Status</th>
                <th>Chunks</th>
                <th>Uploaded</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => (
                <tr key={document.document_id}>
                  <td>{document.filename}</td>
                  <td>{document.document_id}</td>
                  <td>
                    <span className={styles.status}>Ready</span>
                  </td>
                  <td>{document.chunk_count}</td>
                  <td>{new Date(document.uploaded_at).toLocaleString()}</td>
                  <td>
                    <button
                      className={styles.deleteButton}
                      onClick={() => void onDelete(document.document_id)}
                      type="button"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
