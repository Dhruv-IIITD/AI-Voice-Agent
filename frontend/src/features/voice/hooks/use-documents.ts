"use client";

import { useCallback, useEffect, useState } from "react";

import { deleteDocument, fetchDocuments, uploadDocument } from "../lib/api-client";
import { toUserFriendlyBackendError } from "../lib/error-utils";
import type { DocumentSummary } from "../types";

const DEFAULT_LOAD_ERROR = "Unable to load documents from the knowledge base.";
const DEFAULT_UPLOAD_ERROR = "Unable to upload this document.";
const DEFAULT_DELETE_ERROR = "Unable to delete this document.";

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetchDocuments();
      setDocuments(response);
      setError(null);
    } catch (caughtError) {
      setError(toUserFriendlyBackendError(caughtError, DEFAULT_LOAD_ERROR));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  const uploadDocumentFile = useCallback(async (file: File) => {
    setIsUploading(true);
    try {
      const document = await uploadDocument(file);
      setDocuments((current) => [
        document,
        ...current.filter((item) => item.document_id !== document.document_id)
      ]);
      setError(null);
    } catch (caughtError) {
      setError(toUserFriendlyBackendError(caughtError, DEFAULT_UPLOAD_ERROR));
    } finally {
      setIsUploading(false);
    }
  }, []);

  const deleteDocumentById = useCallback(async (documentId: string) => {
    try {
      await deleteDocument(documentId);
      setDocuments((current) => current.filter((item) => item.document_id !== documentId));
      setError(null);
    } catch (caughtError) {
      setError(toUserFriendlyBackendError(caughtError, DEFAULT_DELETE_ERROR));
    }
  }, []);

  return {
    documents,
    isLoading,
    isUploading,
    error,
    refreshDocuments,
    uploadDocumentFile,
    deleteDocumentById
  };
}
