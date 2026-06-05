"""Deterministic fix verification.

The Critic's weakness is that it only *reasons* about a fix. This module *proves* it:
apply the proposed patch to a throwaway copy of the project and run its tests. The
verdict is the test's real exit code — never an LLM's opinion. The real project is
never touched; all edits happen in a temp copy that is deleted afterwards.
"""

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

# Trees we don't copy into the verification sandbox (noise / huge / irrelevant).
_IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", ".venv", "node_modules", "pgdata", ".mypy_cache", ".pytest_cache"
)


class CodeEdit(BaseModel):
    """A single, exact source edit — structured so it can be applied deterministically."""

    file: str = Field(description="Path to the file to change, relative to the project root.")
    old: str = Field(description="Exact existing snippet to replace; must match the file verbatim.")
    new: str = Field(description="Replacement snippet.")
    explanation: str = Field(default="", description="Why this change resolves the failure.")


@dataclass
class VerifyResult:
    passed: bool      # did the test command succeed after applying the patch?
    applied: bool     # did the patch actually match and get applied?
    output: str       # test output (or the reason the patch couldn't be applied)


def apply_and_test(target_dir: str, edit: CodeEdit, test_command: str) -> VerifyResult:
    """Apply `edit` on a copy of `target_dir`, run `test_command`, return the real result."""
    src = Path(target_dir).resolve()
    tmp_root = Path(tempfile.mkdtemp(prefix="sherlog-verify-"))
    try:
        repo = tmp_root / "repo"
        shutil.copytree(src, repo, ignore=_IGNORE)

        target_file = repo / edit.file
        if not target_file.is_file():
            return VerifyResult(False, False, f"Patch target not found: {edit.file}")

        content = target_file.read_text()
        if edit.old not in content:
            # The proposed `old` snippet must exist verbatim, or we can't safely apply it.
            snippet = edit.old[:80]
            return VerifyResult(False, False, f"Patch didn't match {edit.file}: '{snippet}'")

        # Apply exactly once to avoid accidental multi-site edits.
        target_file.write_text(content.replace(edit.old, edit.new, 1))

        try:
            proc = subprocess.run(
                test_command, shell=True, cwd=repo, capture_output=True, text=True, timeout=120
            )
        except subprocess.TimeoutExpired:
            return VerifyResult(False, True, f"Test command timed out: {test_command}")

        output = f"exit_code={proc.returncode}\n{proc.stdout}\n{proc.stderr}".strip()[:4000]
        return VerifyResult(passed=proc.returncode == 0, applied=True, output=output)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
