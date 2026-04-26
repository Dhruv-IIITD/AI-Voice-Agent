from __future__ import annotations


def build_orchestrator_prompt(
    agent_system_prompt: str,
    *,
    memory_context: str = "",
    rag_context: str = "",
    tool_context: str = "",
) -> str:
    prompt = (
        f"{agent_system_prompt}\n\n"
        "You are responding in a real-time voice conversation.\n"
        "Use short, natural sentences that are easy to speak aloud.\n"
    )

    if memory_context.strip():
        prompt += (
            "Session memory context is available below. Use it for follow-up questions and references like "
            "'that', 'it', or 'earlier'.\n\n"
            f"Session memory context:\n{memory_context}\n\n"
        )

    if rag_context.strip():
        prompt += (
            "You also have context from user-uploaded documents.\n"
            "If the context is relevant, answer using it and naturally mention the answer is based on uploaded documents.\n"
            "If context is not relevant, continue normally without inventing document facts.\n\n"
            f"Uploaded document context:\n{rag_context}\n\n"
        )

    if tool_context.strip():
        prompt += (
            "Tool results are available below.\n"
            "Use them when they are relevant, and respond in a natural voice-friendly way.\n\n"
            f"Tool results:\n{tool_context}\n\n"
        )

    prompt += "Return plain text only."
    return prompt
