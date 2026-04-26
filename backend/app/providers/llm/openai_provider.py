from __future__ import annotations

import warnings
from typing import Any


class OpenAILLMClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "OpenAILLMClient is deprecated. Use LangChain + LangGraph orchestration in app.agent.",
            DeprecationWarning,
            stacklevel=2,
        )
        raise RuntimeError(
            "OpenAILLMClient has been removed from the runtime flow. Use ConversationSession/VoiceAgentGraph."
        )
