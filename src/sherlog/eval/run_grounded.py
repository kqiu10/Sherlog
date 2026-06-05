"""Grounded-gain evaluation (B): does tool access make diagnosis more correct?

For each code-rooted case (a tiny repo whose failure log shows only a symptom, with
the real cause in the code) we diagnose twice on the SAME model, self-correction OFF:

  - log-only      : the agent sees only the failure log
  - tool-augmented: the agent can read the project's code (read-only MCP tools)

    accuracy(tool-augmented) - accuracy(log-only) = grounded gain

Holding the model and the loop fixed isolates the effect of *access to the code* — a
value that doesn't depend on the model being weak (see docs/strategy). Run it:

    uv run python -m sherlog.eval.run_grounded
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from sherlog.config import settings
from sherlog.eval.judge import judge_root_cause
from sherlog.graph import build_graph

CASES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "eval" / "code_rooted"
RESULTS_DIR = Path(__file__).parent.parent.parent.parent / "eval" / "results"
console = Console()


def _load_cases() -> list[dict]:
    cases = []
    for d in sorted(CASES_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta = json.loads((d / "meta.json").read_text())
        meta["log"] = (d / "failure.log").read_text()
        meta["repo"] = str((d / "repo").resolve())
        cases.append(meta)
    return cases


async def _root_cause(graph, log: str) -> str:
    result = await graph.ainvoke({"raw_log": log})
    return result.get("root_cause", "")


async def evaluate() -> dict:
    cases = _load_cases()
    report: dict = {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": settings.sherlog_model,
        "n_cases": len(cases),
        "per_case": [],
    }

    # Log-only graph has no project access; it's the same for every case.
    log_only_graph = build_graph(self_correction=False)
    log_correct = tool_correct = 0

    for case in cases:
        rc_log = await _root_cause(log_only_graph, case["log"])
        j_log = judge_root_cause(case["log"], case["expected_root_cause"], rc_log)

        # Tool-augmented graph is scoped to this case's repo (read-only tools).
        tool_graph = build_graph(self_correction=False, target_dir=case["repo"])
        rc_tool = await _root_cause(tool_graph, case["log"])
        j_tool = judge_root_cause(case["log"], case["expected_root_cause"], rc_tool)

        log_correct += j_log.passed
        tool_correct += j_tool.passed
        report["per_case"].append({
            "id": case["id"],
            "title": case["title"],
            "log_only_passed": j_log.passed,
            "tool_passed": j_tool.passed,
        })
        lo = "[green]✓[/green]" if j_log.passed else "[red]✗[/red]"
        to = "[green]✓[/green]" if j_tool.passed else "[red]✗[/red]"
        console.print(f"  {case['id']}: log-only {lo}  tool-augmented {to}  — {case['title']}")

    n = len(cases)
    report["accuracy_log_only"] = log_correct / n if n else 0.0
    report["accuracy_tool"] = tool_correct / n if n else 0.0
    report["grounded_gain"] = report["accuracy_tool"] - report["accuracy_log_only"]
    return report


def _print_summary(report: dict) -> None:
    table = Table(title="Sherlog — Grounded Gain (log-only vs tool-augmented)")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    n = report["n_cases"]
    table.add_row("Cases (code-rooted)", str(n))
    table.add_row("Model", report["model"])
    table.add_row("Accuracy — log-only", f"{report['accuracy_log_only']:.0%}")
    table.add_row("Accuracy — tool-augmented", f"{report['accuracy_tool']:.0%}")
    table.add_row("Grounded gain", f"{report['grounded_gain']:+.0%}")
    console.print()
    console.print(table)


def main() -> None:
    argparse.ArgumentParser(description="Run the grounded-gain evaluation.").parse_args()
    report = asyncio.run(evaluate())
    _print_summary(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_file = RESULTS_DIR / f"grounded-{stamp}.json"
    out_file.write_text(json.dumps(report, indent=2))
    console.print(f"\nSaved detailed results to [cyan]{out_file}[/cyan]")


if __name__ == "__main__":
    main()
