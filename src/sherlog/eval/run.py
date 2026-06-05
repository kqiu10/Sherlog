"""Evaluation runner: measure root-cause accuracy and the self-correction gain.

For every labeled case we run the pipeline twice — once with the Critic loop on,
once off (the ablation) — judge each diagnosis against the human label, and report:

    accuracy(with)  -  accuracy(without)  =  self-correction gain

Run it:

    uv run python -m sherlog.eval.run            # full set
    uv run python -m sherlog.eval.run --limit 3  # quick smoke run

Results print as a table and are saved to eval/results/ (gitignored).
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from sherlog.config import settings
from sherlog.eval.judge import judge_root_cause
from sherlog.graph import build_graph

CASES_FILE = Path(__file__).parent.parent.parent.parent / "data" / "eval" / "cases.json"
RESULTS_DIR = Path(__file__).parent.parent.parent.parent / "eval" / "results"
console = Console()

MODES = {
    "with_self_correction": True,
    "without_self_correction": False,
}


def _run_case(graph, log: str) -> dict:
    """Run one log through a compiled graph; return the fields we score on."""
    result = graph.invoke({"raw_log": log})
    return {
        "root_cause": result.get("root_cause", ""),
        "iterations": result.get("iterations", 0),
    }


def evaluate(limit: int | None = None) -> dict:
    cases = json.loads(CASES_FILE.read_text())
    if limit:
        cases = cases[:limit]

    report: dict = {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": settings.sherlog_model,
        "n_cases": len(cases),
        "modes": {},
    }

    for mode_name, self_correction in MODES.items():
        console.print(f"\n[bold]Running mode: {mode_name}[/bold] ({len(cases)} cases)")
        graph = build_graph(self_correction=self_correction)
        per_case = []

        for case in cases:
            out = _run_case(graph, case["log"])
            verdict = judge_root_cause(case["log"], case["expected_root_cause"], out["root_cause"])
            per_case.append({
                "id": case["id"],
                "title": case["title"],
                "passed": verdict.passed,
                "score": verdict.score,
                "iterations": out["iterations"],
                "actual_root_cause": out["root_cause"],
                "reason": verdict.reason,
            })
            mark = "[green]✓[/green]" if verdict.passed else "[red]✗[/red]"
            console.print(f"  {mark} {case['id']} (score {verdict.score:.2f})")

        correct = sum(1 for c in per_case if c["passed"])
        report["modes"][mode_name] = {
            "accuracy": correct / len(cases) if cases else 0.0,
            "correct": correct,
            "total": len(cases),
            "per_case": per_case,
        }

    acc_with = report["modes"]["with_self_correction"]["accuracy"]
    acc_without = report["modes"]["without_self_correction"]["accuracy"]
    report["self_correction_gain"] = acc_with - acc_without
    return report


def _print_summary(report: dict) -> None:
    table = Table(title="Sherlog Evaluation")
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    with_m = report["modes"]["with_self_correction"]
    without_m = report["modes"]["without_self_correction"]
    with_str = f"{with_m['accuracy']:.0%} ({with_m['correct']}/{with_m['total']})"
    without_str = f"{without_m['accuracy']:.0%} ({without_m['correct']}/{without_m['total']})"
    table.add_row("Cases", str(report["n_cases"]))
    table.add_row("Accuracy — with self-correction", with_str)
    table.add_row("Accuracy — without (ablation)", without_str)
    table.add_row("Self-correction gain", f"{report['self_correction_gain']:+.0%}")
    console.print()
    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Sherlog evaluation.")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N cases.")
    args = parser.parse_args()

    report = evaluate(limit=args.limit)
    _print_summary(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_file = RESULTS_DIR / f"eval-{stamp}.json"
    out_file.write_text(json.dumps(report, indent=2))
    console.print(f"\nSaved detailed results to [cyan]{out_file}[/cyan]")


if __name__ == "__main__":
    main()
