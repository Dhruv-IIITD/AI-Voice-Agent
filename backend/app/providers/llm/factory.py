from __future__ import annotations

import warnings
from typing import Any


def build_llm_client(*args: Any, **kwargs: Any) -> None:
    warnings.warn(
        "build_llm_client is deprecated. LLM orchestration now runs through app.agent.graph + app.agent.llm.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise RuntimeError(
        "Direct LLM client factory has been removed. Use ConversationSession/VoiceAgentGraph instead."
    )
