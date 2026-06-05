"""Wire the agent nodes into a LangGraph pipeline.

P2 topology (RAG, no Critic yet):

    START -> ingest -> retrieve -> diagnose -> report -> END

The next phase adds a `fix -> critic` loop that can route back to `diagnose` (P3).
Because each node only reads/writes fields on DiagnosisState, adding it won't
disturb this wiring.
"""

from langgraph.graph import END, START, StateGraph

from sherlog.agents.diagnostician import diagnose
from sherlog.agents.ingest import ingest
from sherlog.agents.reporter import report
from sherlog.agents.retriever import retrieve
from sherlog.state import DiagnosisState


def build_graph():
    graph = StateGraph(DiagnosisState)

    graph.add_node("ingest", ingest)
    graph.add_node("retrieve", retrieve)
    graph.add_node("diagnose", diagnose)
    graph.add_node("report", report)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "retrieve")
    graph.add_edge("retrieve", "diagnose")
    graph.add_edge("diagnose", "report")
    graph.add_edge("report", END)

    return graph.compile()
