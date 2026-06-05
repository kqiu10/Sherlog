"""Diagnostician node: identify the single most likely root cause.

Two variants share the same inputs (log + retrieved context + any Critic feedback):

- `diagnose` (sync): log-only reasoning. Used when there's no project to inspect
  (e.g. the eval cases, which are bare logs).
- `make_tool_diagnose(target_dir)` (async): an investigator that calls the read-only
  MCP tools (read_file / search_code) to look at the actual code before concluding.
  Used when the CLI is given a target repo. This is what lets the diagnosis rest on
  evidence the log alone doesn't contain. Running code is reserved for the
  deterministic verify step, so investigation can never mutate the project.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from sherlog.llm import get_llm
from sherlog.mcp_client import load_read_tools
from sherlog.state import DiagnosisState

SYSTEM_PROMPT = """You are an expert SRE/diagnostics engineer.
Given a failure log, identify the single most likely root cause.
Be specific and concrete. Respond in 2-4 sentences. State the root cause first,
then the key evidence from the log that supports it."""

INVESTIGATE_SYSTEM = """You are an expert SRE/diagnostics engineer with read-only tools to
inspect the project under diagnosis: read_file and search_code.
Investigate before concluding: read the source the log/stack-trace points at.
Then give the single most likely root cause in 2-4 sentences — state the root cause
first, then the concrete evidence (file/line) that supports it."""


def _user_content(state: DiagnosisState) -> str:
    """Assemble the diagnosis prompt from the log, retrieved context, and Critic feedback."""
    parts = [f"FAILURE LOG:\n{state.get('parsed_log', '')}"]
    context = "\n\n".join(state.get("retrieved_context", []))
    if context:
        parts.append(f"SIMILAR PAST INCIDENTS:\n{context}")
    feedback = state.get("critic_verdict", "")
    if feedback:
        parts.append(f"A previous attempt was rejected. Reviewer feedback:\n{feedback}")
    return "\n\n".join(parts)


def make_diagnose(model: str | None = None):
    """Build a log-only diagnose node, optionally on a specific model (e.g. Haiku)."""

    def diagnose(state: DiagnosisState) -> DiagnosisState:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=_user_content(state)),
        ]
        response = get_llm(model).invoke(messages)
        return {"root_cause": response.content}

    return diagnose


def make_tool_diagnose(target_dir: str, model: str | None = None):
    """Build a tool-using diagnose node bound to a project directory (and optional model)."""

    async def diagnose_with_tools(state: DiagnosisState) -> DiagnosisState:
        # Read-only investigation: the agent can inspect the code but never mutate it.
        tools = await load_read_tools(target_dir)
        agent = create_react_agent(get_llm(model), tools, prompt=INVESTIGATE_SYSTEM)
        result = await agent.ainvoke({"messages": [("user", _user_content(state))]})
        return {"root_cause": result["messages"][-1].content}

    return diagnose_with_tools
