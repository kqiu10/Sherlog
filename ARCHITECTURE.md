# Architecture

This document explains how Sherlog works, component by component, and the design
decisions behind it.

## The thesis

A diagnosis tool wrapped around a strong LLM is only worth building if it adds value the
model **cannot get on its own** — no matter how smart the model is. Two such values:

1. **Access to evidence the model can't see** — the actual source code, the real test
   output. The model can only reason about what's in its context; it can't read a file it
   was never shown.
2. **Verification against reality** — running the fix and observing a green test, instead
   of trusting the model's confident-but-fallible judgment.

Everything in Sherlog serves one of those two. "Make the model reason harder" (a reflection
loop) is deliberately *not* the headline, because that value shrinks as models improve. See
[Results](README.md#results) for the measurements that back this up.

## Pipeline

Sherlog is a [LangGraph](https://langchain-ai.github.io/langgraph/) state machine:

```
START → ingest → retrieve → diagnose → propose_fix → gate ──pass──→ report → END
                               ▲                        │
                               └────── fail, retry < N ─┘
```

Every node reads and writes fields on a single shared `DiagnosisState` (a `TypedDict`).
A node returns a partial update that LangGraph merges in. Keeping the data flow in one
typed structure makes the pipeline explicit and each node independently testable.

### `ingest` (`agents/ingest.py`)

Trims the raw log and caps it at 12k characters, **keeping the tail** — the actual error
and stack trace are almost always at the end. Deliberately simple; smarter parsing can
replace the body without changing the interface.

### `retrieve` (`agents/retriever.py`) — RAG

Embeds the parsed log (local `fastembed` / `bge-small`, 384-dim — no second API key) and
runs a cosine-similarity search (`<=>`) over an `incidents` table in Postgres + **pgvector**.
The top-k similar past incidents — each with its resolved root cause and fix — become
grounding context for the diagnostician.

**Fail-soft:** if the DB is unreachable or empty, it returns no context so the pipeline
still produces a diagnosis. Retrieval *sharpens* the answer; it isn't required for one.

The knowledge base is seeded from `data/incidents/seed.json` (`scripts/seed_incidents.py`)
and is intended to grow over time as resolved incidents are written back.

### `diagnose` (`agents/diagnostician.py`)

Two variants, chosen by `build_graph`:

- **Log-only** (`make_diagnose`) — reasons from the log + retrieved context alone. Used when
  there's no project to inspect (e.g. eval cases that are bare logs).
- **Tool-using** (`make_tool_diagnose`) — a `create_react_agent` given **read-only** MCP
  tools (`read_file`, `search_code`). It reads the actual source the stack trace points at
  before concluding. Used when the CLI is given `--target-dir`.

The model is configurable (`get_llm(model)`), so the eval can run a cheaper diagnostician
in an ablation.

### `propose_fix` (`agents/fix_proposer.py`)

- **Free-text** (`propose_fix`) — a prose fix, used on the log-only path.
- **Structured** (`make_structured_fix`) — a tool-using agent investigates, then a separate
  `with_structured_output(CodeEdit)` call emits a `{file, old, new}` patch that can be
  applied deterministically. Used when a target repo + test command are available.

> Why two steps instead of `create_react_agent(response_format=...)`? LangGraph's prebuilt
> structured-output path uses assistant-message *prefill*, which Anthropic rejects. So the
> agent investigates in free form, then a structured call (fed the file contents it read)
> produces a patch whose `old` matches the file verbatim.

### The gate — `critic` or `verify`

The gate decides whether the diagnosis+fix is good enough to report, or should loop back to
`diagnose` with feedback. There are three configurations:

| Configuration | Gate | Verdict source |
|---|---|---|
| `--target-dir` + `--test-command` | **`verify`** (`agents/verifier.py`) | **Real test exit code** (proof) |
| self-correction only | **`critic`** (`agents/critic.py`) | LLM judgment (opinion) |
| `--no-self-correction` | none | — (ablation baseline) |

Both gates emit the same `critic_verdict` field (starting with `PASS`/`FAIL`), so the
routing is identical for either one. `_route_after_critic` sends the run back to `diagnose`
on failure (with the verdict as feedback) until it passes or hits `SHERLOG_MAX_ITERATIONS` —
a hard cap so a stubborn case always terminates.

**The verifier** is deterministic: it copies the project to a temp sandbox, applies the
`CodeEdit`, runs the test command, and reports the real pass/fail. No LLM is involved in the
verdict (`verify.py::apply_and_test`).

### `report` (`agents/reporter.py`)

Pure formatting (no LLM). Assembles the root cause, proposed fix, and verification verdict
into one Markdown report.

## The MCP tool layer

Tools are exposed over the **Model Context Protocol** by a standalone server
(`mcp_server.py`, built on `FastMCP`, stdio transport). The LangGraph agents are MCP
*clients* (via `langchain-mcp-adapters`), spawning the server as a subprocess scoped to the
target project (`SHERLOG_TARGET_DIR`).

| Tool | Purpose |
|---|---|
| `read_file` | Read a source file the stack trace points at |
| `search_code` | Regex-grep the project for a symbol/message |
| `run_command` | Run tests/lint/build (used only by the verifier) |

Why MCP rather than direct function tools? For a single app it isn't strictly necessary —
but exposing the tools over MCP makes them reusable by any MCP client, sandboxes them in
their own process, and follows the emerging standard for agent tooling.

## Security model

Sherlog can point an LLM at a real codebase, so the tool surface is least-privilege:

- **Read-only investigation.** `diagnose` and `propose_fix` get only `read_file` /
  `search_code` (`load_read_tools`). An agent can never modify or execute the project it is
  diagnosing.
- **Side effects only in a sandbox.** The only tool that runs commands is used by the
  deterministic verifier, against a **throwaway copy** (`copytree` → apply → test → delete).
  The original project is never the working directory — asserted by a test.
- **Path confinement.** All file access resolves under the target directory; traversal
  (`../../etc/passwd`) is rejected.
- **Bounded loops.** `SHERLOG_MAX_ITERATIONS` guarantees termination.

## Evaluation (`eval/`)

Designed to measure value that holds on a **strong** model, not value manufactured by using
a weak one.

- **`judge.py`** — an LLM-as-judge (DeepEval `GEval` with Claude as the judge model) scores
  whether a diagnosis captures the same root cause as a human label. Free-text answers can't
  be string-matched, so a rubric-driven judge is used.
- **`run.py`** — self-correction ablation (Critic on vs off). *Finding: ≈0 gain on a strong
  model — reflection alone is not the value.*
- **`run_grounded.py` (B)** — log-only vs tool-augmented diagnosis on code-rooted cases
  (failure shows a symptom, cause is in the code). *Measures the grounding gain.*
- **`run_gates.py` (C)** — candidate fixes through both gates, scored against whether the
  test actually passes. *Measures verification reliability vs LLM opinion.*

Eval data lives in `data/eval/` and is kept **disjoint** from the RAG seed set to avoid
leakage.

## Tech choices

| Choice | Why |
|---|---|
| LangGraph | Explicit stateful graph with conditional edges/loops — fits a self-correcting agent |
| pgvector | SQL + vector search in one store; production-realistic |
| fastembed (local) | Local embeddings → the only credential needed is the Claude key |
| MCP | Standard, reusable, sandboxed tool interface |
| DeepEval GEval | Standard LLM-as-judge; pointed at Claude (no second vendor key) |
| uv | Fast, reproducible Python dependency management |

## Map of the code

```
src/sherlog/
├── config.py          # typed settings (key, model, DB URL, max iterations)
├── state.py           # DiagnosisState (the shared graph state)
├── llm.py             # get_llm(model) — Claude client, cached per model
├── embeddings.py      # local fastembed embedder (384-dim)
├── db.py              # pgvector access: schema + similarity search
├── mcp_server.py      # MCP server: read_file / search_code / run_command
├── mcp_client.py      # load MCP tools (all / read-only) into LangChain
├── verify.py          # CodeEdit + deterministic apply-and-test (sandbox)
├── graph.py           # build_graph(...) — wires nodes, picks gate, routing
├── cli.py             # `sherlog diagnose` (typer)
├── agents/            # ingest · retriever · diagnostician · fix_proposer · critic · verifier · reporter
└── eval/              # judge · run (ablation) · run_grounded (B) · run_gates (C)
```
