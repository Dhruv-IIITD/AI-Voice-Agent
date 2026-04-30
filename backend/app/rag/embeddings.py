from __future__ import annotations

import logging

from chromadb.api.types import EmbeddingFunction
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logger = logging.getLogger(__name__)


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_embedding_function() -> EmbeddingFunction:
    """
    Returns a SentenceTransformer embeddings.
    """

    logger.info("[RAG] Using local SentenceTransformer embeddings model=%s", EMBEDDING_MODEL)

    return SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
    )