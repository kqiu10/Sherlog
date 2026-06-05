"""Wire the agent nodes into a LangGraph pipeline.

P1 topology (linear, no RAG/Critic yet):

    START -> ingest -> diagnose -> report -> END

Later phases insert a `retrieve` node before `diagnose` (P2) and a
`fix -> critic` loop that can route back to `diagnose` (P3). Because each node
only reads/writes fields on DiagnosisState, adding them won't disturb this wiring.
"""

from langgraph.graph import END, START, StateGraph

from sherlog.agents.diagnostician import diagnose
from sherlog.agents.ingest import ingest
from sherlog.agents.reporter import report
from sherlog.state import DiagnosisState


def build_graph():
    graph = StateGraph(DiagnosisState)

    graph.add_node("ingest", ingest)
    graph.add_node("diagnose", diagnose)
    graph.add_node("report", report)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "diagnose")
    graph.add_edge("diagnose", "report")
    graph.add_edge("report", END)

    return graph.compile()
