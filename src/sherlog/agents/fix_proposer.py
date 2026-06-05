"""Fix Proposer node: turn a root-cause hypothesis into a concrete, actionable fix.

Separating "what's broken" (Diagnostician) from "how to fix it" (here) keeps each
agent's job small and reviewable, and gives the Critic two distinct things to check:
is the root cause right, and would this fix actually resolve it?
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from sherlog.llm import get_llm
from sherlog.mcp_client import load_read_tools
from sherlog.state import DiagnosisState
from sherlog.verify import CodeEdit

SYSTEM_PROMPT = """You are a senior engineer proposing a concrete fix for a diagnosed failure.
Given the failure log and the identified root cause, propose a specific, actionable fix.
Prefer a minimal change that directly addresses the root cause. If useful, include a short
code snippet or the exact command/config change. Respond in 2-5 sentences."""

INVESTIGATE_FIX_SYSTEM = """You are a senior engineer fixing a diagnosed failure.
Use the tools to read the exact source you intend to change. Then describe the minimal
fix, quoting the exact existing code to change and the replacement. Fix the actual
defect — never edit test files just to force a pass."""

STRUCTURE_FIX_SYSTEM = """Convert the engineer's proposed fix into ONE structured code edit.
The `old` field MUST be copied VERBATIM from the provided file contents so it matches the
file character-for-character (keep it small but unique enough to match exactly once).
Set `file` to the path relative to the project root."""


def propose_fix(state: DiagnosisState) -> DiagnosisState:
    """Free-text fix proposal (log-only path, no project access)."""
    log = state.get("parsed_log", "")
    root_cause = state.get("root_cause", "")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"FAILURE LOG:\n{log}\n\nIDENTIFIED ROOT CAUSE:\n{root_cause}"),
    ]
    response = get_llm().invoke(messages)

    return {"proposed_fix": response.content}


def make_structured_fix(target_dir: str):
    """Build a tool-using fix proposer that emits a deterministically-applicable CodeEdit.

    Two steps, because Claude rejects create_react_agent's prefill-based structured output:
    (1) a tool-using agent investigates and drafts the fix in free form; (2) a separate
    structured-output call turns that draft into a CodeEdit, fed the exact file contents
    the agent read so the `old` snippet matches the file verbatim.
    """

    async def propose_structured_fix(state: DiagnosisState) -> DiagnosisState:
        tools = await load_read_tools(target_dir)
        agent = create_react_agent(get_llm(), tools, prompt=INVESTIGATE_FIX_SYSTEM)
        content = (
            f"FAILURE LOG:\n{state.get('parsed_log', '')}\n\n"
            f"IDENTIFIED ROOT CAUSE:\n{state.get('root_cause', '')}"
        )
        result = await agent.ainvoke({"messages": [("user", content)]})
        draft = result["messages"][-1].content

        # Gather the file contents the agent actually read (the ToolMessages), so the
        # structuring step can copy the `old` snippet verbatim. Tool content may be a
        # list of blocks, so coerce to str.
        seen = [str(m.content) for m in result["messages"] if getattr(m, "type", "") == "tool"]
        investigation = "\n\n".join(seen)[:8000]

        structurer = get_llm().with_structured_output(CodeEdit)
        edit: CodeEdit = await structurer.ainvoke([
            SystemMessage(content=STRUCTURE_FIX_SYSTEM),
            HumanMessage(content=f"PROPOSED FIX:\n{draft}\n\nFILE CONTENTS READ:\n{investigation}"),
        ])

        readable = f"{edit.explanation}\n\n--- {edit.file} ---\n- {edit.old}\n+ {edit.new}"
        # Stash the structured patch for the deterministic verify node.
        return {"proposed_fix": readable, "code_edit": edit.model_dump()}

    return propose_structured_fix
