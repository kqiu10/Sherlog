"""Command-line entry point: `sherlog diagnose <logfile>` (or pipe a log via stdin).

Thin wrapper — it reads the log, runs the LangGraph pipeline, and prints the report.
All the real work lives in the graph/agents so the CLI stays trivial.
"""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

from sherlog.graph import build_graph

app = typer.Typer(help="Sherlog: multi-agent log diagnosis.")
console = Console()


@app.callback()
def _main() -> None:
    """Force Typer to keep subcommand form (`sherlog diagnose ...`) even with one command,
    so adding more commands later doesn't change the existing invocation."""


@app.command()
def diagnose(
    logfile: Path | None = typer.Argument(
        None, help="Path to a failure log. If omitted, read from stdin."
    ),
) -> None:
    """Diagnose the root cause of a failure log."""
    # Accept either a file path or piped stdin (e.g. `cat build.log | sherlog diagnose`).
    if logfile is not None:
        raw_log = logfile.read_text()
    elif not sys.stdin.isatty():
        raw_log = sys.stdin.read()
    else:
        console.print("[red]Provide a log file path or pipe a log via stdin.[/red]")
        raise typer.Exit(code=1)

    graph = build_graph()
    result = graph.invoke({"raw_log": raw_log})

    console.print(Markdown(result["report"]))


if __name__ == "__main__":
    app()
