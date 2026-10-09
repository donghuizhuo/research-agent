# UW Course Research Agent

A read-only UW Seattle course research MVP for CSE and INFO. The agent classifies
the query, retrieves facts only from approved indexed/snapshot sources, and
composes a source-grounded answer with citations and freshness metadata.

## Stack

- Python 3.11+
- LangGraph + SqliteSaver (persistent, resumable workflow state)
- FastAPI + uvicorn (API and static Web UI)
- Typer CLI (ingest, search, serve)
- SQLite + FTS5 (structured retrieval)
- DeepSeek (OpenAI-compatible) as default LLM provider

## Quickstart

```bash
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

courseagent ingest              # fetch + index approved sources
courseagent search "CSE 142"    # run the graph
courseagent serve               # API + Web UI on http://127.0.0.1:8000
```

See `specs/001-course-search/quickstart.md` for full details.
For model setup, see [Model mode](#model-mode).

For a direct course lookup, enter `CSE 143` or
`show me information about the cse 143` in the CLI or Web UI. The latter also
accepts omission of `the`. Course discovery queries such as
`Which courses have CSE 142 as a prerequisite?` continue through discovery search.

## Model mode

Search and API serving default to model mode with the existing configured DeepSeek
provider. Set `DEEPSEEK_API_KEY`, then run `courseagent search "CSE 142"` or
`courseagent serve`; no mode flag is required. Shared `DefaultConfig()` construction
also selects model mode when `COURSEAGENT_LLM_MODE` is absent.

For deterministic catalog rendering, set `COURSEAGENT_LLM_MODE=deterministic` before
starting the CLI or API process, or use `--llm-mode deterministic` with either CLI
command. CLI mode flags override the environment, including `--llm-mode model`.
Programmatic API callers can pass `DefaultConfig(llm_mode="deterministic")` to
`create_app` to bypass the provider.

Both entrypoints use the same quick/deep client construction. DeepSeek uses
`DEEPSEEK_API_KEY` explicitly; an unrelated `OPENAI_API_KEY` does not enable it.
Missing credentials, unsupported runtime providers, or either tier failing to
initialize leave the whole graph deterministic. Invocation errors, including
timeouts, fall back within each node. Requests have no automatic retries and
a fixed 10-second timeout per HTTP transport phase (connect/read/write/pool).
This is a transport bound, not an overall workflow deadline.

Typed course objects, metadata, and citations always come from retrieval, including
when synthesis succeeds. Empty or non-text synthesis uses deterministic prose;
no-results searches skip synthesis. The API schema is unchanged and serializes
catalog results. CLI/graph `answer` may contain generated prose; `structured_answer`
remains the authoritative catalog answer. Model prose is not validated against
catalog facts by this contract fix.

API and CLI queries pass through the existing lexical redactor before graph state,
checkpoint persistence, classification, or synthesis. It masks standalone seven-digit
numbers, email addresses, and labeled NetID/student-ID tokens; it is not comprehensive
sensitive-information detection. Queries containing only redaction placeholders
and punctuation return the normal empty result without classification or synthesis
model calls. Offline regressions capture both tiers’ emitted
prompts and persisted checkpoints for these patterns and check unchanged catalog
results. They do not evaluate live model interpretation or other sensitive formats.
