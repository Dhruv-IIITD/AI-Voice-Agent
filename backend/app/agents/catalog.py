from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.session import AgentSummary


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    description: str
    system_prompt: str
    tool_names: list[str]
    accent_color: str
    direct_response_tool_names: list[str] = field(default_factory=list)

    def as_summary(self) -> AgentSummary:
        preview = self.system_prompt.strip().splitlines()[0]
        return AgentSummary(
            id=self.id,
            name=self.name,
            description=self.description,
            system_prompt_preview=preview,
            tool_names=self.tool_names,
            accent_color=self.accent_color,
        )


AGENTS: dict[str, AgentDefinition] = {
    "support": AgentDefinition(
        id="support",
        name="Support Agent",
        description="Handles product FAQs and can look up demo order statuses for customer support scenarios.",
        tool_names=["lookup_faq", "lookup_order_status"],
        accent_color="#C5522B",
        system_prompt=(
            "You are a concise support agent for a SaaS product demo. "
            "Focus on product FAQs, account help, and order-status style support questions. "
            "Answer clearly, ask one follow-up question at a time, and use tools whenever they can ground the answer. "
            "You are running inside a live demo with real tool access. "
            "Do not claim that you lack tools or external capability when a relevant demo tool is available."
        ),
    ),
    "scheduler": AgentDefinition(
        id="scheduler",
        name="Scheduling Agent",
        description="A simple time helper that answers current-time questions for a requested timezone.",
        tool_names=["current_time"],
        direct_response_tool_names=["current_time"],
        accent_color="#186B5C",
        system_prompt=(
            "You are a scheduling assistant for a browser voice demo. "
            "Focus on current-time and simple timezone questions only. "
            "Keep answers short and practical. "
            "Use the current_time tool for time questions instead of improvising. "
            "You are running inside a live demo with real tool access. "
            "Do not claim that you lack tools or external capability when a relevant demo tool is available."
        ),
    ),
    "calculator": AgentDefinition(
        id="calculator",
        name="Calculator Agent",
        description="A focused arithmetic assistant that solves calculations through a grounded calculator tool.",
        tool_names=["calculate_expression"],
        direct_response_tool_names=["calculate_expression"],
        accent_color="#5E6FD8",
        system_prompt=(
            "You are a calculator assistant for a browser voice demo. "
            "Focus on arithmetic, percentages, and short math explanations only. "
            "Use the calculate_expression tool whenever the user asks for a calculation or numeric result. "
            "Keep answers short, accurate, and grounded in the tool output. "
            "You are running inside a live demo with real tool access. "
            "Do not claim that you lack tools or external capability when a relevant demo tool is available."
        ),
    ),
}

def list_agents() -> list[AgentSummary]:
    result = []
    for agent in AGENTS.values():
        result.append(agent.as_summary())
    return result


def get_agent(agent_id: str) -> AgentDefinition:
    try:
        return AGENTS[agent_id]
    except KeyError as exc:
        raise ValueError(f"Unknown agent '{agent_id}'.") from exc
