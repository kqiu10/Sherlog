"""The shared state object that flows through the LangGraph diagnosis pipeline.

Every agent/node reads fields it needs and writes fields it produces. LangGraph
passes this dict from node to node; each node returns a partial update that gets
merged in. Keeping it one typed structure makes the data flow explicit.
"""

from typing import TypedDict


class DiagnosisState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────
    raw_log: str          # the failure log / build output pasted or piped in
    diff: str             # optional code diff associated with the failure

    # ── Produced by Ingest ─────────────────────────────────
    parsed_log: str       # cleaned / structured version of raw_log

    # ── Produced by Retriever (added in P2) ────────────────
    retrieved_context: list[str]  # similar past incidents / runbook snippets

    # ── Produced by Diagnostician ──────────────────────────
    root_cause: str       # current root-cause hypothesis

    # ── Produced by Fix Proposer + Critic (added in P3) ────
    proposed_fix: str
    critic_verdict: str   # "pass" / "fail" + reasoning
    iterations: int       # self-correction loop counter

    # ── Produced by Reporter ───────────────────────────────
    report: str           # final human-readable conclusion
