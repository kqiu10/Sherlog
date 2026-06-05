# Sherlog

**Multi-agent log diagnosis: finds root cause, proposes fixes, and self-verifies.**

Sherlog is a multi-agent fault-diagnosis tool built on [LangGraph](https://langchain-ai.github.io/langgraph/). It ingests a failure log, retrieves similar historical incidents and code context via RAG (pgvector), hypothesizes the root cause, proposes a fix, and runs a **self-correction loop** where a Critic agent validates the result and feeds back until the diagnosis holds. It ships with rigorous evaluation (RAGAS / DeepEval) so accuracy is reported with real numbers, not just a demo.

> Status: early development. End-to-end pipeline (ingest → RAG retrieve → diagnose → propose fix → self-correct → report) runs today, including MCP tool-use and an eval harness. Rigorous accuracy numbers on a hardened eval set are in progress.

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

# 4. Diagnose a failure log (log-only reasoning)
uv run sherlog diagnose data/samples/npm_build_failure.log
# ...or pipe one in:
cat build.log | uv run sherlog diagnose

# 5. Diagnose WITH tool access — the agent reads the project's code (via MCP)
#    instead of reasoning from the log alone:
uv run sherlog diagnose examples/buggy_calculator/failure.log \
  --target-dir examples/buggy_calculator

# 6. ...and PROVE the fix — apply it to a throwaway copy and run the tests:
uv run sherlog diagnose examples/buggy_calculator/failure.log \
  --target-dir examples/buggy_calculator \
  --test-command "python -m pytest -q"
```

### MCP tools

When `--target-dir` is set, the agents investigate the project through an MCP server
(`sherlog.mcp_server`) exposing three tools, sandboxed to that directory:

| Tool | What it does |
|------|--------------|
| `read_file` | Read a source file the stack trace points at |
| `search_code` | Regex-grep the project for a symbol or message |
| `run_command` | Run a command (used only by the verifier, on a copy) |

Diagnosis and fix-proposal use the **read-only** tools, so investigation can never
mutate the project.

### Deterministic verification (proof, not opinion)

With `--test-command`, the gate stops being an LLM judgment. The fix proposer emits a
**structured patch** (`file` / `old` / `new`); the verifier copies the project to a
temp sandbox, applies the patch, and runs your test command. The verdict is the test's
real exit code. If it still fails, the loop retries with that feedback. The original
project is never modified.

## Development

```bash
uv run pytest        # run tests
uv run ruff check .  # lint
```

## License

MIT — see [LICENSE](LICENSE).
