"""Fix Proposer node: turn a root-cause hypothesis into a concrete, actionable fix.

Separating "what's broken" (Diagnostician) from "how to fix it" (here) keeps each
agent's job small and reviewable, and gives the Critic two distinct things to check:
is the root cause right, and would this fix actually resolve it?
"""

from langchain_core.messages import HumanMessage, SystemMessage

from sherlog.llm import get_llm
from sherlog.state import DiagnosisState

SYSTEM_PROMPT = """You are a senior engineer proposing a concrete fix for a diagnosed failure.
Given the failure log and the identified root cause, propose a specific, actionable fix.
Prefer a minimal change that directly addresses the root cause. If useful, include a short
code snippet or the exact command/config change. Respond in 2-5 sentences."""


def propose_fix(state: DiagnosisState) -> DiagnosisState:
    log = state.get("parsed_log", "")
    root_cause = state.get("root_cause", "")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"FAILURE LOG:\n{log}\n\nIDENTIFIED ROOT CAUSE:\n{root_cause}"),
    ]
    response = get_llm().invoke(messages)

    return {"proposed_fix": response.content}
