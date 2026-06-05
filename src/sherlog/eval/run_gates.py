"""Gate benchmark (C): deterministic verification vs the LLM critic.

Each candidate fix is run through both gates:
  - LLM critic     : reasons about the fix description -> PASS/FAIL (an opinion)
  - deterministic  : applies the patch to a copy and runs the tests -> PASS/FAIL (ground truth)

Ground truth is whether the test actually passes, so the verifier is correct by
construction. The interesting number is how many *plausible-but-wrong* fixes the LLM
critic approves that the verifier catches (e.g. "use round()", which sounds right but
returns 2.34 for 2.345 due to float representation, so the test fails).

    uv run python -m sherlog.eval.run_gates
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from sherlog.agents.critic import critique, verdict_passed
from sherlog.verify import CodeEdit, apply_and_test

BENCH_FILE = Path(__file__).parent.parent.parent.parent / "data" / "eval" / "gate_bench.json"
CASES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "eval" / "code_rooted"
RESULTS_DIR = Path(__file__).parent.parent.parent.parent / "eval" / "results"
console = Console()


def evaluate() -> dict:
    candidates = json.loads(BENCH_FILE.read_text())
    report: dict = {"timestamp": datetime.now(UTC).isoformat(), "candidates": []}

    for cand in candidates:
        case_dir = CASES_DIR / cand["case"]
        meta = json.loads((case_dir / "meta.json").read_text())
        log = (case_dir / "failure.log").read_text()
        repo = str((case_dir / "repo").resolve())

        # Ground truth = the deterministic verifier: apply the patch, run the tests.
        works = apply_and_test(repo, CodeEdit(**cand["code_edit"]), meta["test_command"]).passed

        # The LLM critic only sees the fix *description* and reasons about it.
        critic_state = {
            "parsed_log": log,
            "root_cause": meta["expected_root_cause"],
            "proposed_fix": cand["fix_description"],
        }
        critic_pass = verdict_passed(critique(critic_state)["critic_verdict"])

        report["candidates"].append({
            "id": cand["id"],
            "actually_works": works,
            "critic_pass": critic_pass,
            "verifier_pass": works,  # the verifier's verdict IS the test result
            "critic_correct": critic_pass == works,
        })
        gt = "[green]works[/green]" if works else "[red]broken[/red]"
        cr = "PASS" if critic_pass else "FAIL"
        catch = "  [yellow]<- verifier caught it[/yellow]" if (critic_pass and not works) else ""
        console.print(f"  {cand['id']:22} truth={gt:18} critic={cr}{catch}")

    n = len(candidates)
    critic_correct = sum(c["critic_correct"] for c in report["candidates"])
    broken = [c for c in report["candidates"] if not c["actually_works"]]
    false_accepts = [c for c in broken if c["critic_pass"]]  # critic approved a broken fix
    report.update({
        "n": n,
        "verifier_accuracy": 1.0,  # ground truth by construction
        "critic_accuracy": critic_correct / n if n else 0.0,
        "broken_fixes": len(broken),
        "broken_fixes_caught_by_verifier": len(broken),
        "broken_fixes_approved_by_critic": len(false_accepts),
    })
    return report


def _print_summary(report: dict) -> None:
    table = Table(title="Sherlog — Gate Benchmark (verifier vs LLM critic)")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Candidate fixes", str(report["n"]))
    table.add_row("Broken fixes in set", str(report["broken_fixes"]))
    caught = f"{report['broken_fixes_caught_by_verifier']}/{report['broken_fixes']}"
    table.add_row("Verifier accuracy (vs ground truth)", f"{report['verifier_accuracy']:.0%}")
    table.add_row("LLM critic accuracy (vs ground truth)", f"{report['critic_accuracy']:.0%}")
    table.add_row("Broken fixes caught by verifier", caught)
    approved = str(report["broken_fixes_approved_by_critic"])
    table.add_row("...wrongly approved by the LLM critic", approved)
    console.print()
    console.print(table)


def main() -> None:
    report = evaluate()
    _print_summary(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_file = RESULTS_DIR / f"gates-{stamp}.json"
    out_file.write_text(json.dumps(report, indent=2))
    console.print(f"\nSaved detailed results to [cyan]{out_file}[/cyan]")


if __name__ == "__main__":
    main()
