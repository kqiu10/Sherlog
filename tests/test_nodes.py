"""Unit tests for the non-LLM pipeline nodes.

These run with no API key and no network: they verify the deterministic plumbing
(ingest trimming, report formatting) so we can refactor confidently. The LLM-backed
diagnose node is covered separately with mocks / eval, not here.
"""

from sherlog.agents.ingest import MAX_LOG_CHARS, ingest
from sherlog.agents.reporter import report


def test_ingest_strips_and_passes_through():
    out = ingest({"raw_log": "  hello error  \n"})
    assert out["parsed_log"] == "hello error"


def test_ingest_caps_length_keeping_tail():
    # The real error is at the end, so ingest must keep the tail, not the head.
    out = ingest({"raw_log": "X" * (MAX_LOG_CHARS + 50) + "TAIL"})
    assert len(out["parsed_log"]) == MAX_LOG_CHARS
    assert out["parsed_log"].endswith("TAIL")


def test_report_renders_root_cause():
    out = report({"root_cause": "Null baseUrl passed to fetch."})
    assert "# Sherlog Diagnosis" in out["report"]
    assert "Null baseUrl" in out["report"]


def test_report_includes_fix_and_iterations_when_present():
    out = report({
        "root_cause": "x",
        "proposed_fix": "guard the undefined",
        "iterations": 2,
    })
    assert "Proposed Fix" in out["report"]
    assert "2 self-correction" in out["report"]
