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

export DEEPSEEK_API_KEY="..."   # optional; deterministic path works without it

courseagent ingest              # fetch + index approved sources
courseagent search "CSE 142"    # run the graph
courseagent serve               # API + Web UI on http://127.0.0.1:8000
```

See `specs/001-course-search/quickstart.md` for full details.
