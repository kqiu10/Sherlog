"""Retriever node: pull similar past incidents from the pgvector knowledge base.

Embeds the current (parsed) log and runs a cosine-similarity search over stored
incidents. The top matches — each with its resolved root cause and fix — are
formatted into `retrieved_context`, which the Diagnostician then reasons over.

Designed to fail soft: if the DB is unreachable or empty, it returns no context
so the pipeline still produces a diagnosis (just without RAG grounding).
"""

from sherlog.db import search_similar
from sherlog.embeddings import embed
from sherlog.state import DiagnosisState

TOP_K = 3


def retrieve(state: DiagnosisState) -> DiagnosisState:
    log = state.get("parsed_log", "")
    if not log:
        return {"retrieved_context": []}

    try:
        matches = search_similar(embed(log), k=TOP_K)
    except Exception:
        # Fail soft: no RAG grounding is better than crashing the whole diagnosis.
        return {"retrieved_context": []}

    context = [
        f"Past incident: {m['title']}\n"
        f"Resolved root cause: {m['root_cause']}\n"
        f"Fix that worked: {m['fix'] or 'n/a'}"
        for m in matches
    ]
    return {"retrieved_context": context}
