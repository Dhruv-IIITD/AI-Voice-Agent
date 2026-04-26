from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

from app.agent.memory import SessionMemory
from app.agent.tools.document_tools import search_uploaded_docs
from app.agent.tools.mock_tools import create_mock_ticket
from app.agent.tools.session_tools import get_session_context, summarize_conversation
from app.tools.calculator import calculate_expression
from app.tools.current_time import get_current_time
from app.tools.faq import lookup_faq
from app.tools.order_status import lookup_order_status

logger = logging.getLogger(__name__)

ToolName = Literal[
    "search_uploaded_docs",
    "summarize_conversation",
    "create_mock_ticket",
    "get_session_context",
    "current_time",
    "calculate_expression",
    "lookup_order_status",
    "lookup_faq",
]


@dataclass(frozen=True)
class ToolDecision:
    name: ToolName | None
    arguments: dict[str, object]


@dataclass(frozen=True)
class ToolExecution:
    name: ToolName
    arguments: dict[str, object]
    result: dict[str, object]
    result_summary: str


class AgentToolbox:
    def decide_tool(
        self,
        *,
        user_text: str,
        memory: SessionMemory,
        retrieved_chunks: list[dict[str, object]] | None = None,
        available_tools: list[str] | None = None,
    ) -> ToolDecision:
        normalized = user_text.lower().strip()
        if not normalized:
            return ToolDecision(name=None, arguments={})
        enabled_tools = {tool.strip() for tool in (available_tools or []) if tool.strip()}

        def is_enabled(tool_name: str) -> bool:
            if tool_name in {"search_uploaded_docs", "summarize_conversation", "create_mock_ticket", "get_session_context"}:
                return True
            if not enabled_tools:
                return True
            return tool_name in enabled_tools

        if self._is_ticket_request(normalized):
            title, description = self._parse_ticket_fields(user_text)
            return ToolDecision(
                name="create_mock_ticket",
                arguments={
                    "title": title,
                    "description": description,
                },
            )

        if self._is_conversation_summary_request(normalized):
            return ToolDecision(name="summarize_conversation", arguments={})

        if self._is_session_context_request(normalized):
            return ToolDecision(name="get_session_context", arguments={})

        if is_enabled("search_uploaded_docs") and self._is_document_search_request(
            normalized, retrieved_chunks=retrieved_chunks or []
        ):
            query = self._extract_document_query(user_text)
            if not query:
                query = user_text
            return ToolDecision(
                name="search_uploaded_docs",
                arguments={"query": query},
            )

        if is_enabled("current_time") and self._is_time_request(normalized):
            return ToolDecision(
                name="current_time",
                arguments={"timezone": self._extract_timezone_argument(user_text)},
            )

        if is_enabled("calculate_expression") and self._is_calculation_request(normalized, user_text):
            return ToolDecision(
                name="calculate_expression",
                arguments={"expression": user_text},
            )

        if is_enabled("lookup_order_status") and self._is_order_status_request(normalized):
            order_id = self._extract_order_id(user_text)
            return ToolDecision(
                name="lookup_order_status",
                arguments={"order_id": order_id},
            )

        if is_enabled("lookup_faq") and self._is_faq_request(normalized):
            return ToolDecision(
                name="lookup_faq",
                arguments={"question": user_text},
            )

        return ToolDecision(name=None, arguments={})

    async def execute(self, decision: ToolDecision, *, memory: SessionMemory) -> ToolExecution | None:
        if not decision.name:
            return None

        logger.info("[ToolCall] Selected tool: %s", decision.name)
        logger.info("[ToolCall] Input: %s", decision.arguments)

        try:
            if decision.name == "search_uploaded_docs":
                query = str(decision.arguments.get("query") or "")
                result = search_uploaded_docs(query)
                summary = str(result.get("summary") or f"Retrieved {result.get('chunk_count', 0)} chunks.")
            elif decision.name == "summarize_conversation":
                result = summarize_conversation(memory)
                summary = str(result.get("summary") or "Conversation summary generated.")
            elif decision.name == "create_mock_ticket":
                title = str(decision.arguments.get("title") or "")
                description = str(decision.arguments.get("description") or "")
                result = create_mock_ticket(title, description)
                summary = f"Created mock ticket {result.get('ticket_id')}."
            elif decision.name == "get_session_context":
                result = get_session_context(memory)
                summary = "Returned recent session context."
            elif decision.name == "current_time":
                timezone_value = str(decision.arguments.get("timezone") or "")
                tool_output = await get_current_time({"timezone": timezone_value})
                result = {"timezone": timezone_value, "text": tool_output}
                summary = tool_output
            elif decision.name == "calculate_expression":
                expression = str(decision.arguments.get("expression") or "")
                tool_output = await calculate_expression({"expression": expression})
                result = {"expression": expression, "text": tool_output}
                summary = tool_output
            elif decision.name == "lookup_order_status":
                order_id = str(decision.arguments.get("order_id") or "")
                tool_output = await lookup_order_status({"order_id": order_id})
                result = {"order_id": order_id, "text": tool_output}
                summary = tool_output
            elif decision.name == "lookup_faq":
                question = str(decision.arguments.get("question") or "")
                tool_output = await lookup_faq({"question": question})
                result = {"question": question, "text": tool_output}
                summary = tool_output
            else:
                return None
        except Exception as exc:
            logger.exception("[ToolCall] Tool execution failed name=%s", decision.name)
            result = {"error": str(exc)}
            summary = (
                f"{decision.name} could not complete. Please continue without this tool result."
            )

        logger.info("[ToolCall] Result summary: %s", summary)
        return ToolExecution(
            name=decision.name,
            arguments=decision.arguments,
            result=result,
            result_summary=summary,
        )

    def _is_document_search_request(self, normalized: str, *, retrieved_chunks: list[dict[str, object]]) -> bool:
        doc_markers = (
            "document",
            "uploaded",
            "file",
            "pdf",
            "doc",
        )
        search_markers = (
            "search",
            "find",
            "mentioned",
            "summarize",
            "technolog",
        )
        mentions_it = " in it" in normalized or normalized.startswith("what about it")
        if any(marker in normalized for marker in doc_markers) and any(marker in normalized for marker in search_markers):
            return True
        if mentions_it and any(marker in normalized for marker in search_markers):
            return True
        if mentions_it and bool(retrieved_chunks):
            return True
        if normalized.startswith("summarize the uploaded document"):
            return True
        return False

    def _is_time_request(self, normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in (
                "current time",
                "what time",
                "time in",
                "time now",
                "timezone",
            )
        )

    def _extract_timezone_argument(self, user_text: str) -> str:
        lowered = user_text.lower()
        if "india" in lowered or "ist" in lowered or "kolkata" in lowered:
            return "Asia/Kolkata"
        if "utc" in lowered or "gmt" in lowered:
            return "UTC"
        match = re.search(r"\b([A-Za-z]+/[A-Za-z_]+)\b", user_text)
        if match:
            return match.group(1)
        in_match = re.search(r"\btime in ([A-Za-z ]+)\??$", user_text, flags=re.IGNORECASE)
        if in_match:
            return in_match.group(1).strip()
        return "UTC"

    def _is_calculation_request(self, normalized: str, user_text: str) -> bool:
        if "calculate" in normalized:
            return True
        if self._looks_like_math_request(user_text):
            return True
        return False

    def _looks_like_math_request(self, user_text: str) -> bool:
        has_operator = bool(re.search(r"[+\-*/^%]", user_text))
        has_digits = bool(re.search(r"\d", user_text))
        has_math_words = any(
            marker in user_text.lower()
            for marker in ("plus", "minus", "times", "multiplied", "divided", "percent", "power")
        )
        return (has_operator and has_digits) or has_math_words

    def _is_order_status_request(self, normalized: str) -> bool:
        return "order" in normalized and any(
            marker in normalized for marker in ("status", "track", "where", "update")
        )

    def _extract_order_id(self, user_text: str) -> str:
        match = re.search(r"\b([A-Za-z]\d{3})\b", user_text)
        if match:
            return match.group(1).upper()
        return ""

    def _is_faq_request(self, normalized: str) -> bool:
        return any(
            marker in normalized
            for marker in ("pricing", "integration", "security", "faq", "what can you help")
        )

    def _is_conversation_summary_request(self, normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in (
                "summarize our conversation",
                "summarise our conversation",
                "conversation so far",
                "summary of our chat",
            )
        )

    def _is_session_context_request(self, normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in (
                "what did i ask",
                "before this",
                "ask earlier",
                "previous question",
            )
        )

    def _is_ticket_request(self, normalized: str) -> bool:
        has_ticket = "ticket" in normalized
        has_action = any(keyword in normalized for keyword in ("create", "open", "make"))
        return has_ticket and has_action

    def _extract_document_query(self, user_text: str) -> str:
        text = user_text.strip()
        lowered = text.lower()
        prefix_pattern = r"^(search|find|summarize)\s+(my\s+)?(uploaded\s+)?(documents?|files?)\s*(for|about)?\s*"
        text = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip()
        if text:
            return text
        if "technolog" in lowered:
            return "technologies mentioned in uploaded documents"
        return user_text.strip()

    def _parse_ticket_fields(self, user_text: str) -> tuple[str, str]:
        text = user_text.strip()
        lowered = text.lower()

        description = text
        for marker in ("saying", "about", "for"):
            index = lowered.find(f" {marker} ")
            if index != -1:
                description = text[index + len(marker) + 2 :].strip()
                break

        if not description:
            description = "Voice session issue reported by user."

        title = description[:80]
        return title, description
