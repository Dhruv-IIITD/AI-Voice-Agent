from __future__ import annotations

import json
from typing import Any

from app.tools.base import ToolDefinition
from app.tools.calculator import calculate_expression
from app.tools.current_time import get_current_time
from app.tools.faq import lookup_faq
from app.tools.order_status import lookup_order_status


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {
            "current_time": ToolDefinition(
                name="current_time",
                description="Look up the current time in a timezone.",
                parameters={
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "IANA timezone like Asia/Kolkata or America/New_York.",
                        }
                    },
                    "required": [],
                },
                handler=get_current_time,
            ),
            "lookup_faq": ToolDefinition(
                name="lookup_faq",
                description="Search a tiny FAQ knowledge base for pricing, integrations, or security.",
                parameters={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The user question to match against the FAQ.",
                        }
                    },
                    "required": ["question"],
                },
                handler=lookup_faq,
            ),
            "lookup_order_status": ToolDefinition(
                name="lookup_order_status",
                description="Return a demo order status from a hardcoded support data set.",
                parameters={
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "Demo order ID like A100, B205, or C309.",
                        }
                    },
                    "required": ["order_id"],
                },
                handler=lookup_order_status,
            ),
            "calculate_expression": ToolDefinition(
                name="calculate_expression",
                description="Safely evaluate a basic arithmetic expression and return the result.",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Arithmetic expression or short math request to evaluate.",
                        }
                    },
                    "required": ["expression"],
                },
                handler=calculate_expression,
            ),
        }

    def definitions_for(self, tool_names: list[str]) -> list[ToolDefinition]:
        return [self._tools[name] for name in tool_names if name in self._tools]

    def tools_for(self, tool_names: list[str]) -> list[dict[str, Any]]:
        return [tool.as_openai_tool() for tool in self.definitions_for(tool_names)]

    def format_inventory(self, tool_names: list[str]) -> str:
        tool_lines = []
        for tool in self.definitions_for(tool_names):
            params = tool.parameters.get("properties", {})
            param_names = ", ".join(params.keys()) if params else "no arguments"
            tool_lines.append(f"- {tool.name}: {tool.description} Parameters: {param_names}.")

        if not tool_lines:
            return "No tools are available for this agent."

        return "Available tools:\n" + "\n".join(tool_lines)

    def summarize_inventory(self, tool_names: list[str]) -> str:
        summaries = []
        for tool in self.definitions_for(tool_names):
            summaries.append(f"{tool.name}: {tool.description}")

        if not summaries:
            return "This agent does not have any tools configured."

        return "This agent can use these tools: " + " ".join(summaries)

    async def execute(self, tool_name: str, raw_arguments: str) -> tuple[dict[str, Any], str]:
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered.")
        try:
            parsed = json.loads(raw_arguments) if raw_arguments else {}
        except json.JSONDecodeError:
            parsed = {}
        result = await self._tools[tool_name].handler(parsed)
        return parsed, result
