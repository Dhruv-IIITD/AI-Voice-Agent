from __future__ import annotations

import logging
from dataclasses import dataclass

from langgraph.graph import END, START, StateGraph

from app.agent.llm import generate_response_text
from app.agent.memory import SessionMemory
from app.agent.prompts import build_prompt
from app.agent.state import AgentState, ChatHistoryMessage
from app.agents.catalog import AgentDefinition
from app.rag.retriever import retrieve_serialized_chunks

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentGraphResult:
    response_text: str
    retrieved_chunks: list[dict[str, object]]
    memory_summary: str


class VoiceAgentGraph:
    """Simple LangGraph RAG workflow: retrieve context -> generate response -> update memory."""

    def __init__(self, *, agent: AgentDefinition) -> None:
        self._agent = agent
        builder = StateGraph(AgentState)

        builder.add_node("retrieve_context", self._retrieve_context)
        builder.add_node("generate_response", self._generate_response)
        builder.add_node("update_memory", self._update_memory)

        builder.add_edge(START, "retrieve_context")
        builder.add_edge("retrieve_context", "generate_response")
        builder.add_edge("generate_response", "update_memory")
        builder.add_edge("update_memory", END)

        self._graph = builder.compile()

    async def run(
        self,
        *,
        user_text: str,
        session_memory: SessionMemory,
        history: list[ChatHistoryMessage],
    ) -> AgentGraphResult:
        logger.info("[AgentGraph] Received transcript agent=%s text=%s", self._agent.id, user_text)

        initial_state: AgentState = {
            "user_text": user_text,
            "session_memory": session_memory,
            "history": list(history),
            "retrieved_chunks": [],
            "rag_context": "",
            "response_text": "",
            "memory_summary": "",
        }

        result = await self._graph.ainvoke(initial_state)
        final_text = str(result.get("response_text") or "").strip()
        retrieved_chunks = list(result.get("retrieved_chunks") or [])
        memory_summary = str(result.get("memory_summary") or session_memory.summarize_conversation())

        logger.info(
            "[AgentGraph] Final response generated agent=%s text_length=%s chunks=%s",
            self._agent.id,
            len(final_text),
            len(retrieved_chunks),
        )
        return AgentGraphResult(
            response_text=final_text,
            retrieved_chunks=retrieved_chunks,
            memory_summary=memory_summary,
        )

    async def _retrieve_context(self, state: AgentState) -> AgentState:
        # retrieve_context gets relevant chunks from uploaded documents.
        user_text = str(state.get("user_text") or "")
        try:
            retrieved_chunks = retrieve_serialized_chunks(user_text)
        except Exception:
            logger.exception("[RAG] Retrieval failed, continuing without document context.")
            return {
                "retrieved_chunks": [],
                "rag_context": "",
            }

        rag_context = "\n\n".join(
            (
                f"[{chunk.get('filename', 'uploaded-document')} | chunk {chunk.get('chunk_index', 0)}]\n"
                f"{chunk.get('content', '')}"
            )
            for chunk in retrieved_chunks
        )
        return {
            "retrieved_chunks": retrieved_chunks,
            "rag_context": rag_context,
        }

    async def _generate_response(self, state: AgentState) -> AgentState:
        # generate_response builds the prompt and calls the LLM once.
        system_prompt = build_prompt(
            self._agent.system_prompt,
            rag_context=str(state.get("rag_context") or ""),
            user_text=str(state.get("user_text") or ""),
        )
        response_text = await generate_response_text(
            system_prompt=system_prompt,
            history=list(state["history"]),
        )
        return {"response_text": response_text}

    async def _update_memory(self, state: AgentState) -> AgentState:
        # update_memory saves the user and assistant turns for memory summary/debug.
        user_text = str(state.get("user_text") or "").strip()
        response_text = str(state.get("response_text") or "").strip()
        if user_text:
            state["session_memory"].add_user_turn(user_text)
        if response_text:
            state["session_memory"].add_assistant_turn(response_text)
        return {"memory_summary": state["session_memory"].summarize_conversation()}
