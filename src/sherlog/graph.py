"""Wire the agent nodes into a LangGraph pipeline.

P3 topology (RAG + self-correction loop):

    START -> ingest -> retrieve -> diagnose -> propose_fix -> critic --(PASS)--> report -> END
                                       ▲                          │
                                       └──────(FAIL & iter<N)─────┘

The `critic` node uses a *conditional edge*: a routing function inspects its verdict
and the iteration count, then sends the run either back to `diagnose` (informed by the
Critic's feedback) or onward to `report`. The loop is bounded by SHERLOG_MAX_ITERATIONS
so a stubborn case still terminates with a best-effort report.

`build_graph(self_correction=False)` drops the critic and loop entirely. That's the
ablation baseline used to measure how much the self-correction loop actually helps.
"""

from langgraph.graph import END, START, StateGraph

from sherlog.agents.critic import critique, verdict_passed
from sherlog.agents.diagnostician import diagnose
from sherlog.agents.fix_proposer import propose_fix
from sherlog.agents.ingest import ingest
from sherlog.agents.reporter import report
from sherlog.agents.retriever import retrieve
from sherlog.config import settings
from sherlog.state import DiagnosisState


def _route_after_critic(state: DiagnosisState) -> str:
    """Decide where to go after the Critic: retry the diagnosis, or finalize."""
    if verdict_passed(state.get("critic_verdict", "")):
        return "report"  # Critic accepted — we're done.
    if state.get("iterations", 0) >= settings.sherlog_max_iterations:
        return "report"  # Out of retries — report the best effort anyway.
    return "diagnose"  # Rejected with feedback — try again.


def build_graph(self_correction: bool = True):
    graph = StateGraph(DiagnosisState)

    graph.add_node("ingest", ingest)
    graph.add_node("retrieve", retrieve)
    graph.add_node("diagnose", diagnose)
    graph.add_node("propose_fix", propose_fix)
    graph.add_node("report", report)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "retrieve")
    graph.add_edge("retrieve", "diagnose")
    graph.add_edge("diagnose", "propose_fix")

    if self_correction:
        # Full loop: propose_fix -> critic -> (diagnose | report)
        graph.add_node("critic", critique)
        graph.add_edge("propose_fix", "critic")
        graph.add_conditional_edges(
            "critic",
            _route_after_critic,
            {"diagnose": "diagnose", "report": "report"},
        )
    else:
        # Ablation baseline: skip the critic, go straight to the report.
        graph.add_edge("propose_fix", "report")

    graph.add_edge("report", END)

    return graph.compile()
