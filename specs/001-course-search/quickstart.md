# Quickstart: MVP UW Course Search (Python + LangGraph)

This guide matches the implemented Python/LangGraph stack. All commands below
are runnable from the repository root.

## Prerequisites

- Python 3.11+ (3.13 recommended).
- `uv` (or any PEP 621-compatible installer) for dependency management.
- Optional `DEEPSEEK_API_KEY` for LLM-based query understanding and answer
  synthesis. The deterministic path works without it.

## Setup

```bash
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Expected outcome:

- The `courseagent` package installs with all dependencies.
- `courseagent --help` lists `ingest`, `search`, and `serve` commands.

## Validate source registry

```bash
python -m pytest tests/test_source_registry.py -q
```

Expected outcome:

- `config/sources.yml` loads successfully.
- Only the approved CSE/INFO seed sources are accepted.
- Unregistered URLs are rejected.

## Manual snapshot import

```bash
courseagent ingest
```

Expected outcome:

- A new `snapshot_id` is created.
- Raw HTML snapshots are stored under `data/snapshots/{snapshot_id}/`.
- CSE and INFO catalog courses are normalized into Course records.
- Allen School and UW Informatics pages are indexed as supporting context.
- Every indexed source carries `retrieved_at` and `indexed_at` metadata.

To import a subset:

```bash
courseagent ingest uw_cse_catalog uw_info_catalog
```

## Run the API + Web UI

```bash
courseagent serve
```

Expected outcome:

- API and static UI start at `http://127.0.0.1:8000`.
- `POST /course-search` accepts `{"query": "CSE 142"}`.
- `GET /courses/{course_id}` returns course detail with citations.
- `GET /workflows/{workflow_id}` returns persisted workflow state.
- `GET /workflows/nonexistent` returns a controlled 404.

## Search exact course code (CLI)

```bash
courseagent search "CSE 142"
```

Expected outcome:

- A grounded answer with title, description, credits, citations, and freshness.

## Search department / keyword / natural language

```bash
courseagent search "INFO courses"
courseagent search "programming"
courseagent search "introductory programming course"
```

Expected outcome:

- Ranked results with per-course citations and snapshot-only limitations.

## Run the full test suite

```bash
python -m pytest -q
```

## Run golden validation cases

```bash
python validation/run_validation.py
```

Expected outcome:

- `8/8 golden cases passed`, covering exact lookup, department, keyword,
  natural-language, missing-field, live-only, and workflow-state scenarios.
