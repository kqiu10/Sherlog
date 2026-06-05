"""Sherlog MCP server: tools that let the diagnosis agents gather real evidence.

Instead of reasoning from the log alone, the agents can call these tools (over the
Model Context Protocol) to look at the actual project being diagnosed:

  - read_file(path)      : read a source file the log/stack-trace points at
  - search_code(pattern) : grep the project for a symbol or message
  - run_command(command) : run a test/lint/build and see what really happens

All access is confined to SHERLOG_TARGET_DIR (the project under diagnosis) so the
tools can't wander outside it. Core logic lives in the plain `_*` functions; the
`@mcp.tool()` wrappers just expose them over MCP, which keeps them unit-testable.

Run as a standalone MCP server (stdio):  uv run python -m sherlog.mcp_server
"""

import os
import re
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sherlog-tools")

# Directories we never search/recurse into — noise and huge generated trees.
_SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "pgdata", ".mypy_cache"}
_MAX_CHARS = 10_000  # cap tool output so we don't blow the context window


def _target_root() -> Path:
    """The project being diagnosed. Defaults to CWD; set SHERLOG_TARGET_DIR to point elsewhere."""
    return Path(os.environ.get("SHERLOG_TARGET_DIR", ".")).resolve()


def _safe_path(path: str) -> Path:
    """Resolve `path` under the target root, rejecting any escape (e.g. ../../etc/passwd)."""
    root = _target_root()
    resolved = (root / path).resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"Path '{path}' escapes the target directory")
    return resolved


def _read_file(path: str) -> str:
    p = _safe_path(path)
    if not p.is_file():
        return f"ERROR: '{path}' not found in the target project"
    return p.read_text(errors="ignore")[:_MAX_CHARS]


def _search_code(pattern: str, max_results: int = 30) -> str:
    root = _target_root()
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"ERROR: invalid pattern: {e}"

    hits: list[str] = []
    for p in root.rglob("*"):
        if not p.is_file() or any(part in _SKIP_DIRS for part in p.parts):
            continue
        try:
            for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{p.relative_to(root)}:{i}: {line.strip()[:200]}")
                    if len(hits) >= max_results:
                        return "\n".join(hits)
        except (OSError, UnicodeError):
            continue
    return "\n".join(hits) if hits else "(no matches)"


def _run_command(command: str) -> str:
    # Intentionally runs arbitrary commands — that's the tool's purpose (run tests/lint).
    # Confined to the target dir with a timeout; a real deployment would sandbox harder.
    root = _target_root()
    try:
        result = subprocess.run(
            command, shell=True, cwd=root, capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after 120s: {command}"
    out = (
        f"exit_code={result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    return out[:_MAX_CHARS]


@mcp.tool()
def read_file(path: str) -> str:
    """Read a text file from the project under diagnosis (path is relative to the project root)."""
    return _read_file(path)


@mcp.tool()
def search_code(pattern: str, max_results: int = 30) -> str:
    """Search the project for a regex pattern; returns matching `path:line: text` lines."""
    return _search_code(pattern, max_results)


@mcp.tool()
def run_command(command: str) -> str:
    """Run a shell command (tests, lint, build) in the project; returns its output and exit code."""
    return _run_command(command)


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
