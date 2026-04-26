from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from langgraph.graph import END, START, StateGraph

from app.agent.llm import generate_response_text
from app.agent.memory import SessionMemory
from app.agent.prompts import build_orchestrator_prompt
from app.agent.state import AgentState, ChatHistoryMessage, DeltaCallback
from app.agent.tools import AgentToolbox, ToolDecision, ToolName
from app.agents.catalog import AgentDefinition
from app.rag.retriever import retrieve_serialized_chunks

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentGraphResult:
    response_text: str
    retrieved_chunks: list[dict[str, object]]
    tool_calls: list[dict[str, object]]
    memory_summary: str


class VoiceAgentGraph:
    def __init__(self, *, agent: AgentDefinition) -> None:
        self._agent = agent
        self._toolbox = AgentToolbox()
        builder = StateGraph(AgentState)
        builder.add_node("load_memory", self._load_memory)
        builder.add_node("retrieve_context", self._retrieve_context)
        builder.add_node("decide_tool", self._decide_tool)
        builder.add_node("run_tool", self._run_tool)
        builder.add_node("generate_response", self._generate_response)
        builder.add_node("update_memory", self._update_memory)
        builder.add_edge(START, "load_memory")
        builder.add_edge("load_memory", "retrieve_context")
        builder.add_edge("retrieve_context", "decide_tool")
        builder.add_edge("decide_tool", "run_tool")
        builder.add_edge("run_tool", "generate_response")
        builder.add_edge("generate_response", "update_memory")
        builder.add_edge("update_memory", END)
        self._graph = builder.compile()

    async def run(
        self,
        *,
        user_text: str,
        session_memory: SessionMemory,
        history: list[ChatHistoryMessage],
        on_delta: DeltaCallback | None = None,
    ) -> AgentGraphResult:
        logger.info(
            "[AgentGraph] Received transcript agent=%s text=%s",
            self._agent.id,
            user_text,
        )
        initial_state: AgentState = {
            "user_text": user_text,
            "session_memory": session_memory,
            "history": list(history),
            "response_text": "",
            "retrieved_chunks": [],
            "tool_calls": [],
            "rag_context": "",
            "tool_context": "",
            "memory_context": "",
        }
        if on_delta is not None:
            initial_state["on_delta"] = on_delta

        result = await self._graph.ainvoke(initial_state)
        final_text = str(result.get("response_text") or "").strip()
        retrieved_chunks = list(result.get("retrieved_chunks") or [])
        tool_calls = list(result.get("tool_calls") or [])
        filenames = sorted(
            {
                str(chunk.get("filename", ""))
                for chunk in retrieved_chunks
                if isinstance(chunk, dict) and chunk.get("filename")
            }
        )
        logger.info(
            "[AgentGraph] Final response generated agent=%s text_length=%s chunks=%s tools=%s filenames=%s",
            self._agent.id,
            len(final_text),
            len(retrieved_chunks),
            len(tool_calls),
            filenames,
        )
        return AgentGraphResult(
            response_text=final_text,
            retrieved_chunks=retrieved_chunks,
            tool_calls=tool_calls,
            memory_summary=session_memory.summarize_conversation(),
        )

    async def _load_memory(self, state: AgentState) -> AgentState:
        session_memory = state["session_memory"]
        logger.info("[Memory] Loaded session memory session_id=%s", session_memory.session_id)
        session_memory.add_user_turn(str(state.get("user_text") or ""))
        return {
            "history": session_memory.get_recent_history(limit=12),
            "memory_context": session_memory.build_prompt_context(),
        }

    async def _retrieve_context(self, state: AgentState) -> AgentState:
        user_text = str(state.get("user_text") or "")
        try:
            retrieved_chunks = retrieve_serialized_chunks(user_text)
        except Exception:
            logger.exception("[RAG] Retrieval node failed, falling back to normal conversation path.")
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

    async def _decide_tool(self, state: AgentState) -> AgentState:
        decision = self._toolbox.decide_tool(
            user_text=str(state.get("user_text") or ""),
            memory=state["session_memory"],
            retrieved_chunks=list(state.get("retrieved_chunks") or []),
            available_tools=self._agent.tool_names,
        )
        if decision.name is None:
            return {
                "selected_tool_name": "",
                "selected_tool_arguments": {},
                "tool_calls": [],
                "tool_context": "",
            }
        return {
            "selected_tool_name": decision.name,
            "selected_tool_arguments": decision.arguments,
            "tool_calls": [],
            "tool_context": "",
        }

    async def _run_tool(self, state: AgentState) -> AgentState:
        selected_tool_name = str(state.get("selected_tool_name") or "").strip()
        if not selected_tool_name:
            return {}

        decision = ToolDecision(
            name=cast(ToolName, selected_tool_name),
            arguments=dict(state.get("selected_tool_arguments") or {}),
        )
        execution = await self._toolbox.execute(decision, memory=state["session_memory"])
        if execution is None:
            return {}

        tool_calls = [
            {
                "name": execution.name,
                "arguments": execution.arguments,
                "result_summary": execution.result_summary,
                "result": execution.result,
            }
        ]

        tool_context_lines = [
            f"Tool name: {execution.name}",
            f"Tool summary: {execution.result_summary}",
        ]
        if execution.name == "search_uploaded_docs":
            chunks = execution.result.get("chunks")
            if isinstance(chunks, list) and chunks:
                chunk_lines = []
                for item in chunks[:4]:
                    if not isinstance(item, dict):
                        continue
                    chunk_lines.append(
                        f"[{item.get('filename', 'uploaded-document')} | chunk {item.get('chunk_index', 0)}] {item.get('content', '')}"
                    )
                if chunk_lines:
                    tool_context_lines.append("Retrieved chunks:\n" + "\n".join(chunk_lines))
        elif execution.name == "summarize_conversation":
            summary_text = str(execution.result.get("summary") or "")
            if summary_text:
                tool_context_lines.append("Conversation summary:\n" + summary_text)
        elif execution.name == "get_session_context":
            summary_text = str(execution.result.get("summary") or "")
            if summary_text:
                tool_context_lines.append("Session summary:\n" + summary_text)
            session_payload = execution.result.get("session")
            if isinstance(session_payload, dict):
                recent_turns = session_payload.get("recent_turns")
                if isinstance(recent_turns, list):
                    lines: list[str] = []
                    for item in recent_turns[-6:]:
                        if not isinstance(item, dict):
                            continue
                        lines.append(
                            f"{item.get('role', 'unknown')}: {item.get('text', '')}"
                        )
                    if lines:
                        tool_context_lines.append("Recent turns:\n" + "\n".join(lines))
        elif execution.name == "create_mock_ticket":
            tool_context_lines.append(
                "Ticket created:\n"
                f"id={execution.result.get('ticket_id')} status={execution.result.get('status')} "
                f"title={execution.result.get('title')}"
            )
        else:
            generic_text = str(execution.result.get("text") or "")
            if generic_text:
                tool_context_lines.append("Tool output:\n" + generic_text)

        merged_chunks = list(state.get("retrieved_chunks") or [])
        if execution.name == "search_uploaded_docs":
            chunks = execution.result.get("chunks")
            if isinstance(chunks, list):
                merged_chunks = [item for item in chunks if isinstance(item, dict)]

        return {
            "tool_calls": tool_calls,
            "tool_context": "\n".join(tool_context_lines),
            "retrieved_chunks": merged_chunks,
        }

    async def _generate_response(self, state: AgentState) -> AgentState:
        system_prompt = build_orchestrator_prompt(
            self._agent.system_prompt,
            memory_context=str(state.get("memory_context") or ""),
            rag_context=str(state.get("rag_context") or ""),
            tool_context=str(state.get("tool_context") or ""),
        )
        response_text = await generate_response_text(
            system_prompt=system_prompt,
            history=list(state["history"]),
            on_delta=state.get("on_delta"),
        )
        return {"response_text": response_text}

    async def _update_memory(self, state: AgentState) -> AgentState:
        response_text = str(state.get("response_text") or "").strip()
        if response_text:
            state["session_memory"].add_assistant_turn(response_text)
        return {}
