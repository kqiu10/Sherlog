"""Critic node: review the diagnosis + fix and decide whether to accept or retry.

This is the "reflection" step. The Critic is a separate LLM call with an adversarial
brief: scrutinize the root cause and fix against the actual log, and only accept if
they hold up. On rejection it must give specific, actionable feedback — that feedback
is fed back to the Diagnostician on the next loop so the retry is informed, not random.

Verdict contract: the response MUST start with "PASS" or "FAIL" on the first line,
followed by the reasoning. The graph's routing function keys off that first token.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from sherlog.llm import get_llm
from sherlog.state import DiagnosisState

SYSTEM_PROMPT = """You are a meticulous reviewer validating a failure diagnosis.

You are given the failure log, a proposed root cause, and a proposed fix.
Decide whether the diagnosis is correct and the fix would plausibly resolve the failure.

Respond with exactly one word on the first line: PASS or FAIL.
Then, on the following lines, give a brief justification.

- PASS if the root cause is well-supported by evidence in the log AND the fix
  directly addresses that root cause.
- FAIL only if there is a real problem: the root cause contradicts or ignores the
  log, key evidence is missing, or the fix would not actually resolve the issue.
  When you FAIL, give specific, actionable feedback on what to reconsider.

Do not fail for style or minor wording. Be fair but rigorous."""


def critique(state: DiagnosisState) -> DiagnosisState:
    log = state.get("parsed_log", "")
    root_cause = state.get("root_cause", "")
    proposed_fix = state.get("proposed_fix", "")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"FAILURE LOG:\n{log}\n\n"
                f"PROPOSED ROOT CAUSE:\n{root_cause}\n\n"
                f"PROPOSED FIX:\n{proposed_fix}"
            )
        ),
    ]
    response = get_llm().invoke(messages)

    # Count this review pass so the graph can stop after SHERLOG_MAX_ITERATIONS.
    iterations = state.get("iterations", 0) + 1
    return {"critic_verdict": response.content, "iterations": iterations}


def verdict_passed(verdict: str) -> bool:
    """True if the Critic accepted the diagnosis (verdict starts with PASS)."""
    return verdict.strip().upper().startswith("PASS")
