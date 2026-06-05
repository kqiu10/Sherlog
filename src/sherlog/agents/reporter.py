"""Reporter node: assemble the final human-readable diagnosis report.

Pure formatting — no LLM call. It collects whatever the pipeline produced
(root cause now; fix + verification later) into one Markdown string.
"""

from sherlog.state import DiagnosisState


def report(state: DiagnosisState) -> DiagnosisState:
    root_cause = state.get("root_cause", "(no diagnosis produced)")

    lines = [
        "# Sherlog Diagnosis",
        "",
        "## Root Cause",
        root_cause,
    ]

    # These fields appear once P3 (fix + self-correction) is wired in.
    if state.get("proposed_fix"):
        lines += ["", "## Proposed Fix", state["proposed_fix"]]
    if state.get("iterations"):
        lines += ["", f"_Reached after {state['iterations']} self-correction iteration(s)._"]

    return {"report": "\n".join(lines)}
