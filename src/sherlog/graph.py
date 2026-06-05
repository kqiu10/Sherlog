"""Wire the agent nodes into a LangGraph pipeline.

Full topology (RAG + self-correction loop):

    START -> ingest -> retrieve -> diagnose -> propose_fix -> critic --(PASS)--> report -> END
                                       ▲                          │
                                       └──────(FAIL & iter<N)─────┘

The `critic` node uses a *conditional edge*: a routing function inspects its verdict
and the iteration count, then sends the run either back to `diagnose` (informed by the
feedback) or onward to `report`. The loop is bounded by SHERLOG_MAX_ITERATIONS so a
stubborn case still terminates with a best-effort report.

Three configurations of the gate, chosen by what's available:
  - target_dir + test_command : `verify` — apply the fix to a copy and run the tests
    (deterministic proof). Diagnosis and fix become tool-using; the fix is structured.
  - self_correction only       : `critic` — the LLM reasons about the fix (opinion).
  - self_correction=False       : no gate — straight to report (the ablation baseline).
"""

from langgraph.graph import END, START, StateGraph

from sherlog.agents.critic import critique, verdict_passed
from sherlog.agents.diagnostician import make_diagnose, make_tool_diagnose
from sherlog.agents.fix_proposer import make_structured_fix, propose_fix
from sherlog.agents.ingest import ingest
from sherlog.agents.reporter import report
from sherlog.agents.retriever import retrieve
from sherlog.agents.verifier import make_verify
from sherlog.config import settings
from sherlog.state import DiagnosisState


def _route_after_critic(state: DiagnosisState) -> str:
    """Decide where to go after the gate (Critic/Verifier): retry the diagnosis, or finalize."""
    if verdict_passed(state.get("critic_verdict", "")):
        return "report"  # accepted/proven — we're done.
    if state.get("iterations", 0) >= settings.sherlog_max_iterations:
        return "report"  # out of retries — report the best effort anyway.
    return "diagnose"  # rejected with feedback — try again.


def build_graph(
    self_correction: bool = True,
    target_dir: str | None = None,
    test_command: str | None = None,
    diagnostician_model: str | None = None,
):
    graph = StateGraph(DiagnosisState)

    # Deterministic verification needs both a project to patch and a way to test it.
    verify_mode = bool(self_correction and target_dir and test_command)

    # With a target repo, diagnosis becomes a read-only tool-using investigation;
    # without one it's log-only. Tool nodes are async, so such a graph needs `ainvoke`.
    # diagnostician_model lets the eval run a weaker (cheaper) diagnostician to create
    # the headroom needed to measure the self-correction gain.
    diagnose_node = (
        make_tool_diagnose(target_dir, diagnostician_model)
        if target_dir
        else make_diagnose(diagnostician_model)
    )
    # In verify mode the fix must be a structured patch the verifier can apply.
    fix_node = make_structured_fix(target_dir) if verify_mode else propose_fix

    graph.add_node("ingest", ingest)
    graph.add_node("retrieve", retrieve)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("propose_fix", fix_node)
    graph.add_node("report", report)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "retrieve")
    graph.add_edge("retrieve", "diagnose")
    graph.add_edge("diagnose", "propose_fix")

    if self_correction:
        # The gate is either deterministic verification or the LLM critic; both emit a
        # `critic_verdict`, so the routing below is identical for either one.
        gate = make_verify(target_dir, test_command) if verify_mode else critique
        graph.add_node("critic", gate)
        graph.add_edge("propose_fix", "critic")
        graph.add_conditional_edges(
            "critic",
            _route_after_critic,
            {"diagnose": "diagnose", "report": "report"},
        )
    else:
        # Ablation baseline: skip the gate, go straight to the report.
        graph.add_edge("propose_fix", "report")

    graph.add_edge("report", END)

    return graph.compile()
