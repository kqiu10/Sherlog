"""Verifier node: prove the proposed fix by applying it and running the tests.

This is the deterministic gate (Approach B). Unlike the LLM Critic, it does not *reason*
about whether the fix looks right — it applies the structured patch to a throwaway copy
of the project and runs the real test command. The verdict (PASS/FAIL) is the test's exit
code, not an opinion. It emits the same `critic_verdict` shape as the Critic, so it slots
into the existing self-correction routing unchanged.
"""

from sherlog.state import DiagnosisState
from sherlog.verify import CodeEdit, apply_and_test


def make_verify(target_dir: str, test_command: str):
    """Build a verify node that proves fixes against `test_command` in `target_dir`."""

    def verify(state: DiagnosisState) -> DiagnosisState:
        iterations = state.get("iterations", 0) + 1
        code_edit = state.get("code_edit")

        if not code_edit:
            verdict = "FAIL\nNo structured patch was produced, so nothing could be verified."
            return {"critic_verdict": verdict, "iterations": iterations}

        result = apply_and_test(target_dir, CodeEdit(**code_edit), test_command)
        if result.passed:
            verdict = f"PASS — the fix was applied and the tests passed.\n\n{result.output}"
        elif not result.applied:
            verdict = f"FAIL — the patch could not be applied.\n{result.output}"
        else:
            verdict = f"FAIL — the fix was applied but the tests still fail.\n\n{result.output}"

        return {"critic_verdict": verdict, "iterations": iterations}

    return verify
