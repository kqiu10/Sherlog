# Sherlog

**Multi-agent log diagnosis: finds root cause, proposes fixes, and self-verifies.**

Sherlog is a multi-agent fault-diagnosis tool built on [LangGraph](https://langchain-ai.github.io/langgraph/). It ingests a failure log, retrieves similar historical incidents and code context via RAG (pgvector), hypothesizes the root cause, proposes a fix, and runs a **self-correction loop** where a Critic agent validates the result and feeds back until the diagnosis holds. It ships with rigorous evaluation (RAGAS / DeepEval) so accuracy is reported with real numbers, not just a demo.

> Status: early development. The P1 skeleton (`ingest → diagnose → report`) runs end-to-end; RAG, the self-correction loop, MCP tools, and eval are being added incrementally.

## Architecture

```
  failure log / diff
        │
        ▼
   [Ingest]  ── structured input
        │
        ▼
   [Retriever (RAG)] ◄──── pgvector (similar incidents / runbooks / code)
        │
        ▼
   [Diagnostician] ── root-cause hypothesis
        │
        ▼
   [Fix Proposer] ── proposed fix
        │
        ▼
   [Critic] ──(fail & iterations < N, with feedback)──► back to Diagnostician   ← self-correction loop
        │ pass
        ▼
   [Reporter] ── final report

  Tools (MCP): fetch logs / search code / run lint
```

## Tech stack

LangGraph · Claude (Anthropic) · pgvector · RAGAS / DeepEval · MCP · Python 3.11+

## Quickstart

```bash
# 1. Install dependencies (uses uv)
uv sync

# 2. Configure your Claude API key
cp .env.example .env
# then edit .env and set ANTHROPIC_API_KEY

# 3. Start the pgvector database (needed from P2 onward)
docker compose up -d

# 4. Diagnose a failure log
uv run sherlog diagnose data/samples/npm_build_failure.log
# ...or pipe one in:
cat build.log | uv run sherlog diagnose
```

## Development

```bash
uv run pytest        # run tests
uv run ruff check .  # lint
```

## License

MIT — see [LICENSE](LICENSE).
