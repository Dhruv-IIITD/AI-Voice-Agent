import type { AgentSummary } from "../types";

export interface AgentProfile extends AgentSummary {
  backend_agent_id: string;
  suggested_tools: string[];
  starter_prompts: string[];
}

interface AgentPresentation {
  id: string;
  backendAgentId: string;
  name: string;
  description: string;
  systemPromptPreview: string;
  suggestedTools: string[];
  starterPrompts: string[];
  accentColor: string;
}

const PRESENTATIONS: AgentPresentation[] = [
  {
    id: "document_research",
    backendAgentId: "support",
    name: "Document Research Agent",
    description: "Answers questions using uploaded documents and retrieved context.",
    systemPromptPreview:
      "Use uploaded documents as the primary source and explain answers with grounded, concise reasoning.",
    suggestedTools: ["search_uploaded_docs", "summarize_conversation", "cite_sources"],
    starterPrompts: [
      "Summarize my uploaded document.",
      "Find key responsibilities mentioned in my resume.",
      "List important details from this PDF."
    ],
    accentColor: "#1e7a5e"
  },
  {
    id: "interview_coach",
    backendAgentId: "scheduler",
    name: "Interview Coach Agent",
    description: "Uses uploaded resume and JD documents to conduct mock interviews and give feedback.",
    systemPromptPreview:
      "Act as an interview coach and tailor follow-up questions to the uploaded resume and job description.",
    suggestedTools: ["search_uploaded_docs", "summarize_conversation", "generate_feedback"],
    starterPrompts: [
      "Run a mock interview based on my resume.",
      "Ask me backend engineering interview questions.",
      "Give feedback on my last answer."
    ],
    accentColor: "#375eab"
  },
  {
    id: "project_explainer",
    backendAgentId: "calculator",
    name: "Project Explainer Agent",
    description: "Explains uploaded README files, architecture, tech stack, and improvements.",
    systemPromptPreview:
      "Explain architecture and design decisions clearly, with references to uploaded project docs.",
    suggestedTools: ["search_uploaded_docs", "summarize_conversation"],
    starterPrompts: [
      "Explain this project architecture.",
      "Describe the data flow from voice input to response.",
      "Suggest improvements for production readiness."
    ],
    accentColor: "#8a4e2b"
  },
  {
    id: "technical_tutor",
    backendAgentId: "support",
    name: "Technical Tutor Agent",
    description: "Explains concepts from uploaded notes and docs in simple spoken language.",
    systemPromptPreview:
      "Teach clearly and progressively, using simple explanations grounded in the uploaded notes.",
    suggestedTools: ["search_uploaded_docs", "simplify_explanation"],
    starterPrompts: [
      "Teach me this topic from my notes in simple language.",
      "Explain this concept step by step.",
      "Quiz me on the uploaded study notes."
    ],
    accentColor: "#9f7b1d"
  }
];

export function buildAgentProfiles(backendAgents: AgentSummary[]): AgentProfile[] {
  if (backendAgents.length === 0) {
    return [];
  }

  const backendById = new Map(backendAgents.map((agent) => [agent.id, agent]));
  const fallbackAgent = backendAgents[0];

  return PRESENTATIONS.map((presentation) => {
    const backingAgent = backendById.get(presentation.backendAgentId) ?? fallbackAgent;

    return {
      id: presentation.id,
      backend_agent_id: backingAgent.id,
      name: presentation.name,
      description: presentation.description,
      system_prompt_preview: presentation.systemPromptPreview,
      tool_names: backingAgent.tool_names,
      suggested_tools: presentation.suggestedTools,
      starter_prompts: presentation.starterPrompts,
      accent_color: presentation.accentColor,
      stt_options: backingAgent.stt_options,
      tts_options: backingAgent.tts_options
    };
  });
}

export function createFallbackAgentProfiles(): AgentProfile[] {
  const fallbackOptions = {
    stt_options: ["deepgram", "assemblyai"] as const,
    tts_options: ["elevenlabs", "cartesia"] as const
  };

  return PRESENTATIONS.map((presentation) => ({
    id: presentation.id,
    backend_agent_id: presentation.backendAgentId,
    name: presentation.name,
    description: presentation.description,
    system_prompt_preview: presentation.systemPromptPreview,
    tool_names: [],
    suggested_tools: presentation.suggestedTools,
    starter_prompts: presentation.starterPrompts,
    accent_color: presentation.accentColor,
    stt_options: [...fallbackOptions.stt_options],
    tts_options: [...fallbackOptions.tts_options]
  }));
}
