"""Reporter node: assemble the final human-readable diagnosis report.

Pure formatting — no LLM call. It collects whatever the pipeline produced
(root cause, fix, and the Critic's verification) into one Markdown string.
"""

from sherlog.agents.critic import verdict_passed
from sherlog.state import DiagnosisState


def report(state: DiagnosisState) -> DiagnosisState:
    root_cause = state.get("root_cause", "(no diagnosis produced)")

    lines = [
        "# Sherlog Diagnosis",
        "",
        "## Root Cause",
        root_cause,
    ]

    if state.get("proposed_fix"):
        lines += ["", "## Proposed Fix", state["proposed_fix"]]

    # Verification block only exists when the self-correction loop ran (P3).
    verdict = state.get("critic_verdict")
    if verdict:
        passed = verdict_passed(verdict)
        status = "✅ accepted by Critic" if passed else "⚠️ unresolved after retries"
        iterations = state.get("iterations", 0)
        lines += [
            "",
            "## Verification",
            f"**Status:** {status} after {iterations} self-correction iteration(s).",
            "",
            verdict,
        ]

    return {"report": "\n".join(lines)}
