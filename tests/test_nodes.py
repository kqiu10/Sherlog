"""Unit tests for the non-LLM pipeline nodes.

These run with no API key and no network: they verify the deterministic plumbing
(ingest trimming, report formatting) so we can refactor confidently. The LLM-backed
diagnose node is covered separately with mocks / eval, not here.
"""

from sherlog.agents.critic import verdict_passed
from sherlog.agents.ingest import MAX_LOG_CHARS, ingest
from sherlog.agents.reporter import report
from sherlog.graph import _route_after_critic, build_graph


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
        "critic_verdict": "PASS\nlooks correct",
        "iterations": 2,
    })
    assert "Proposed Fix" in out["report"]
    assert "2 self-correction" in out["report"]
    assert "accepted by Critic" in out["report"]


def test_verdict_passed_parsing():
    assert verdict_passed("PASS\nthe fix is correct")
    assert verdict_passed("  pass — fine")
    assert not verdict_passed("FAIL\nroot cause ignores the stack trace")
    assert not verdict_passed("")


def test_route_passes_to_report_on_pass():
    assert _route_after_critic({"critic_verdict": "PASS", "iterations": 1}) == "report"


def test_route_retries_on_fail_under_budget():
    assert _route_after_critic({"critic_verdict": "FAIL: wrong", "iterations": 1}) == "diagnose"


def test_route_gives_up_at_max_iterations():
    # With the default budget (3), a FAIL at iteration 3 must stop, not loop forever.
    assert _route_after_critic({"critic_verdict": "FAIL", "iterations": 3}) == "report"


def test_both_graph_modes_compile():
    full = build_graph(self_correction=True).get_graph().nodes.keys()
    baseline = build_graph(self_correction=False).get_graph().nodes.keys()
    assert "critic" in full
    assert "critic" not in baseline


def test_tool_diagnose_node_is_async():
    import asyncio

    from sherlog.agents.diagnostician import make_tool_diagnose

    # With a target repo the diagnose node must be async (it awaits the MCP tools).
    assert asyncio.iscoroutinefunction(make_tool_diagnose("/tmp"))


def test_graph_with_target_dir_compiles():
    assert "diagnose" in build_graph(target_dir="/tmp").get_graph().nodes.keys()


def test_verify_mode_graph_compiles():
    # target_dir + test_command activates the deterministic verify gate.
    g = build_graph(target_dir="/tmp", test_command="true")
    assert "critic" in g.get_graph().nodes.keys()
