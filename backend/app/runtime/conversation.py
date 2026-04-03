from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from app.agents.catalog import AgentDefinition
from app.providers.llm.base import BaseLLMClient, ToolCallDirective, ToolPlanningResult
from app.tools.current_time import resolve_timezone_name
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConversationEvent:
    kind: Literal["tool_call", "assistant_delta", "assistant_complete"]
    text: str = ""
    tool_name: str | None = None
    tool_arguments: dict[str, object] | None = None


class ConversationSession:
    def __init__(
        self,
        *,
        agent: AgentDefinition,
        llm_client: BaseLLMClient,
        tool_registry: ToolRegistry,
    ) -> None:
        self._agent = agent
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._history: list[dict[str, object]] = []

    async def stream_reply(self, user_text: str) -> AsyncIterator[ConversationEvent]:
        logger.info("Conversation turn started agent=%s user_text=%s", self._agent.id, user_text)
        self._history.append({"role": "user", "content": user_text})
        tool_schemas = self._tool_registry.tools_for(self._agent.tool_names)
        system_prompt = self._compose_system_prompt()
        inventory_answer = self._inventory_answer_for(user_text)
        if inventory_answer:
            logger.info("Responding with deterministic inventory summary for agent=%s", self._agent.id)
            self._history.append({"role": "assistant", "content": inventory_answer})
            yield ConversationEvent(kind="assistant_complete", text=inventory_answer)
            return
        direct_tool_reply = await self._direct_tool_reply_for(user_text)
        if direct_tool_reply is not None:
            yield direct_tool_reply[0]
            yield direct_tool_reply[1]
            return
        allowed_tool_names = set(self._agent.tool_names)
        tool_messages: list[dict[str, object]] = []
        deterministic_planning = self._fallback_tool_calls(user_text)
        if deterministic_planning.tool_calls and self._should_direct_return(deterministic_planning):
            logger.info(
                "Using deterministic direct-response tool flow agent=%s tool_names=%s",
                self._agent.id,
                [call.name for call in deterministic_planning.tool_calls],
            )
            planning = deterministic_planning
        else:
            logger.info("Planning tool calls with %s available tools", len(tool_schemas))
            planning = await self._llm_client.plan_tool_calls(
                system_prompt=system_prompt,
                history=self._history,
                tools=tool_schemas,
            )
            if not planning.tool_calls:
                planning = deterministic_planning
        logger.info("Tool planning complete tool_call_count=%s", len(planning.tool_calls))

        if planning.tool_calls:
            assistant_tool_calls = []
            for call in planning.tool_calls:
                if call.name not in allowed_tool_names:
                    logger.warning(
                        "Ignoring disallowed tool call agent=%s tool_name=%s allowed_tools=%s",
                        self._agent.id,
                        call.name,
                        sorted(allowed_tool_names),
                    )
                    continue
                logger.info("Executing tool call name=%s", call.name)
                parsed_args, tool_result = await self._tool_registry.execute(call.name, call.arguments)
                logger.info("Tool execution complete name=%s parsed_args=%s", call.name, parsed_args)
                assistant_tool_calls.append(
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": call.arguments,
                        },
                    }
                )
                tool_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": tool_result,
                    }
                )
                yield ConversationEvent(
                    kind="tool_call",
                    tool_name=call.name,
                    tool_arguments=parsed_args,
                )

            self._history.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": assistant_tool_calls,
                }
            )
            self._history.extend(tool_messages)

        if tool_messages and self._should_direct_return(planning):
            final_text = str(tool_messages[-1].get("content") or "").strip()
            logger.info("Returning direct tool result agent=%s text_length=%s", self._agent.id, len(final_text))
            self._history.append({"role": "assistant", "content": final_text})
            self._history = self._history[-14:]
            yield ConversationEvent(kind="assistant_complete", text=final_text)
            return

        full_response_parts: list[str] = []
        try:
            async for delta in self._llm_client.stream_response(
                system_prompt=system_prompt,
                history=self._history,
            ):
                full_response_parts.append(delta)
                yield ConversationEvent(kind="assistant_delta", text=delta)
        except Exception:
            logger.exception("LLM response generation failed")

        final_text = "".join(full_response_parts).strip()
        if not final_text:
            if tool_messages:
                final_text = str(tool_messages[-1].get("content") or "").strip()
            if not final_text:
                final_text = "I'm sorry, I ran into an issue while generating the response."

        logger.info("Conversation stream complete final_text_length=%s", len(final_text))

        self._history.append({"role": "assistant", "content": final_text})
        self._history = self._history[-14:]
        yield ConversationEvent(kind="assistant_complete", text=final_text)

    def _compose_system_prompt(self) -> str:
        inventory = self._tool_registry.format_inventory(self._agent.tool_names)
        return (
            f"{self._agent.system_prompt}\n\n"
            "Tool usage policy:\n"
            "- Use tools whenever they can ground or verify the answer.\n"
            "- Only call tools from the inventory below.\n"
            "- If the user asks what you can do or which tools you can use, answer from the tool inventory below.\n"
            "- When a tool result appears in the conversation history, rely on that result directly in your answer.\n"
            "- Never say that you have no tool or function access if tools are listed below.\n\n"
            f"{inventory}"
        )

    def _inventory_answer_for(self, user_text: str) -> str | None:
        normalized = user_text.lower()
        if "tool" not in normalized and "function" not in normalized and "capabilit" not in normalized:
            return None
        return self._tool_registry.summarize_inventory(self._agent.tool_names)

    async def _direct_tool_reply_for(
        self,
        user_text: str,
    ) -> tuple[ConversationEvent, ConversationEvent] | None:
        if self._agent.id == "scheduler":
            normalized = user_text.lower()
            if not any(keyword in normalized for keyword in ("time", "timezone", "clock", "hour")):
                return None

            timezone = self._extract_time_timezone(user_text)
            raw_arguments = json.dumps({"timezone": timezone})
            logger.info(
                "Using deterministic scheduler direct tool execution timezone=%s user_text=%s",
                timezone,
                user_text,
            )
            parsed_args, tool_result = await self._tool_registry.execute("current_time", raw_arguments)
            self._history.append({"role": "assistant", "content": tool_result})
            self._history = self._history[-14:]
            return (
                ConversationEvent(
                    kind="tool_call",
                    tool_name="current_time",
                    tool_arguments=parsed_args,
                ),
                ConversationEvent(kind="assistant_complete", text=tool_result),
            )

        if self._agent.id == "calculator" and self._looks_like_math_request(user_text):
            raw_arguments = json.dumps({"expression": user_text})
            logger.info("Using deterministic calculator direct tool execution user_text=%s", user_text)
            parsed_args, tool_result = await self._tool_registry.execute("calculate_expression", raw_arguments)
            self._history.append({"role": "assistant", "content": tool_result})
            self._history = self._history[-14:]
            return (
                ConversationEvent(
                    kind="tool_call",
                    tool_name="calculate_expression",
                    tool_arguments=parsed_args,
                ),
                ConversationEvent(kind="assistant_complete", text=tool_result),
            )

        return None

    def _should_direct_return(self, planning: ToolPlanningResult) -> bool:
        if not planning.tool_calls:
            return False
        direct_tools = set(self._agent.direct_response_tool_names)
        if not direct_tools:
            return False
        return all(call.name in direct_tools for call in planning.tool_calls)

    def _fallback_tool_calls(self, user_text: str) -> ToolPlanningResult:
        normalized = user_text.lower()
        available_tools = set(self._agent.tool_names)

        if "lookup_order_status" in available_tools:
            match = re.search(r"\b([A-Za-z]\d{3})\b", user_text)
            if match:
                logger.info("Using fallback tool planner for order status lookup")
                return ToolPlanningResult(
                    tool_calls=[
                        ToolCallDirective(
                            id="fallback-order-status",
                            name="lookup_order_status",
                            arguments=json.dumps({"order_id": match.group(1).upper()}),
                        )
                    ]
                )

        if "current_time" in available_tools and ("time" in normalized or "timezone" in normalized):
            timezone = self._extract_time_timezone(user_text)
            logger.info("Using fallback tool planner for current time lookup")
            return ToolPlanningResult(
                tool_calls=[
                    ToolCallDirective(
                        id="fallback-current-time",
                        name="current_time",
                        arguments=json.dumps({"timezone": timezone}),
                    )
                ]
            )

        if "calculate_expression" in available_tools and self._looks_like_math_request(user_text):
            logger.info("Using fallback tool planner for calculator lookup")
            return ToolPlanningResult(
                tool_calls=[
                    ToolCallDirective(
                        id="fallback-calculator",
                        name="calculate_expression",
                        arguments=json.dumps({"expression": user_text}),
                    )
                ]
            )

        faq_keywords = ("pricing", "integration", "integrations", "security", "faq")
        if "lookup_faq" in available_tools and any(keyword in normalized for keyword in faq_keywords):
            logger.info("Using fallback tool planner for FAQ lookup")
            return ToolPlanningResult(
                tool_calls=[
                    ToolCallDirective(
                        id="fallback-faq",
                        name="lookup_faq",
                        arguments=json.dumps({"question": user_text}),
                    )
                ]
            )

        return ToolPlanningResult(tool_calls=[])

    def _extract_time_timezone(self, user_text: str) -> str:
        timezone_match = re.search(r"\b([A-Za-z]+/[A-Za-z_]+)\b", user_text)
        if timezone_match:
            return resolve_timezone_name(timezone_match.group(1))

        lowered = user_text.lower()
        alias_candidates = [
            "asia/kolkata",
            "america/new_york",
            "america/los_angeles",
            "europe/london",
            "new york",
            "los angeles",
            "california",
            "london",
            "india",
            "indian time",
            "ist",
            "utc",
            "gmt",
            "uk",
            "nyc",
            "pst",
        ]
        for candidate in alias_candidates:
            if candidate in lowered:
                return resolve_timezone_name(candidate)

        return "UTC"

    def _looks_like_math_request(self, user_text: str) -> bool:
        normalized = user_text.lower()
        math_keywords = (
            "calculate",
            "compute",
            "plus",
            "minus",
            "times",
            "multiplied",
            "divided",
            "mod",
            "modulo",
            "power",
            "sum",
            "difference",
            "product",
            "quotient",
        )
        return bool(re.search(r"\d", user_text)) or any(keyword in normalized for keyword in math_keywords)
