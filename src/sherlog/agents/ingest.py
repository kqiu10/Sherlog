"""Ingest node: turn raw failure output into a clean, bounded input for the LLM.

For the P1 skeleton this is deliberately simple — trim whitespace and cap length
so we never blow past the context window. Smarter parsing (stack-trace extraction,
log-line clustering) can replace the body later without changing the interface.
"""

from sherlog.state import DiagnosisState

# Hard cap on characters we feed downstream, to control token cost / context size.
MAX_LOG_CHARS = 12_000


def ingest(state: DiagnosisState) -> DiagnosisState:
    raw = state.get("raw_log", "").strip()

    # Keep the tail: the actual error and stack trace are almost always at the end.
    if len(raw) > MAX_LOG_CHARS:
        raw = raw[-MAX_LOG_CHARS:]

    return {"parsed_log": raw}
