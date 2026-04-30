from __future__ import annotations


def build_prompt(
    agent_system_prompt: str,
    *,
    rag_context: str = "",
    user_text: str = "",
) -> str:
    prompt = (
        f"{agent_system_prompt}\n\n"
        "You are responding in a real-time voice conversation.\n"
        "Use short, natural sentences that are easy to speak aloud.\n\n"
    )

    if rag_context.strip():
        prompt += (
            "Use the uploaded document context only when it is relevant.\n"
            "Do not invent document facts that are not in the provided context.\n\n"
            f"Uploaded document context:\n{rag_context}\n"
        )

    if user_text.strip():
        prompt += f"\nCurrent user request:\n{user_text}\n"

    prompt += "Return plain text only."
    return prompt
