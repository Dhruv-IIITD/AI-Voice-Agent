from __future__ import annotations

import logging
import os

from chromadb.api.types import EmbeddingFunction
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction, OpenAIEmbeddingFunction

logger = logging.getLogger(__name__)


def get_embedding_function() -> EmbeddingFunction:
    provider = os.getenv("RAG_EMBEDDING_PROVIDER", "default").strip().lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning(
                "[RAG] OPENAI_API_KEY missing while RAG_EMBEDDING_PROVIDER=openai; falling back to local embeddings."
            )
            return DefaultEmbeddingFunction()

        model_name = os.getenv("RAG_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        api_base = os.getenv("RAG_OPENAI_BASE_URL")

        logger.info("[RAG] Using OpenAI embeddings model=%s", model_name)
        kwargs: dict[str, str] = {}
        if api_base:
            kwargs["api_base"] = api_base
        return OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name=model_name,
            **kwargs,
        )

    logger.info("[RAG] Using local default embeddings provider=%s", provider)
    return DefaultEmbeddingFunction()
