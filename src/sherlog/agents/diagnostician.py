"""Diagnostician node: ask Claude for the single most likely root cause.

This is the core reasoning step. In P1 it sees only the parsed log; from P2 it
will also receive retrieved historical context, and from P3 it will accept Critic
feedback to revise a previous hypothesis (the self-correction loop).
"""

from langchain_core.messages import HumanMessage, SystemMessage

from sherlog.llm import get_llm
from sherlog.state import DiagnosisState

SYSTEM_PROMPT = """You are an expert SRE/diagnostics engineer.
Given a failure log, identify the single most likely root cause.
Be specific and concrete. Respond in 2-4 sentences. State the root cause first,
then the key evidence from the log that supports it."""


def diagnose(state: DiagnosisState) -> DiagnosisState:
    log = state.get("parsed_log", "")

    # Feed any retrieved context (present from P2 onward) and Critic feedback (P3).
    context = "\n\n".join(state.get("retrieved_context", []))
    feedback = state.get("critic_verdict", "")

    user_parts = [f"FAILURE LOG:\n{log}"]
    if context:
        user_parts.append(f"SIMILAR PAST INCIDENTS:\n{context}")
    if feedback:
        user_parts.append(f"A previous attempt was rejected. Reviewer feedback:\n{feedback}")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content="\n\n".join(user_parts)),
    ]
    response = get_llm().invoke(messages)

    return {"root_cause": response.content}
