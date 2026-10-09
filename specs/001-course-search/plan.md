# Implementation Plan: MVP UW Course Search (LangGraph)

**Feature**: `001-course-search`  
**Spec**: `specs/001-course-search/spec.md`  
**High-level design**: `docs/design/course-search-high-level-design.md`  
**Source registry**: `config/sources.yml`  
**Reference architecture**: `TradingAgents` (multi-agent LangGraph framework)  
**Status**: Draft implementation design  
**Date**: 2026-10-06

## Summary

Build a read-only UW Seattle course research MVP for CSE and INFO as a LangGraph agent. The agent classifies the query, retrieves facts only from approved indexed/snapshot sources, and composes a source-grounded answer with citations and freshness metadata. LangGraph's `SqliteSaver` checkpointer provides the persistent, resumable workflow state required by the constitution.

## Architecture Decision

Mirror `TradingAgents` high-level design:

- **LangGraph `StateGraph`** over a typed `CourseResearchState(MessagesState)`.
- **Conditional routing** (`ConditionalLogic`) from a structured query-intent classifier.
- **Deterministic retrieval nodes** backed by local SQLite/FTS snapshot data (no live UW systems).
- **Grounded answer synthesis** using a deep-tier LLM that may only restate retrieved, cited facts.
- **`SqliteSaver` checkpointer** for per-`workflow_id` persistent, resumable state.
- **Pydantic structured outputs** with `render_*` helpers, matching the TradingAgents schema pattern.

## Technical Context

- **Language/runtime**: Python `>= 3.11`.
- **Orchestration**: `langgraph`, `langchain-core`, `langgraph-checkpoint-sqlite`.
- **LLM clients**: tiered `deep` (answer synthesis) and `quick` (query understanding) clients; **DeepSeek default** via OpenAI-compatible endpoint (`langchain-openai`), provider factory for fallback.
- **API**: FastAPI + uvicorn.
- **CLI**: Typer (mirrors TradingAgents CLI entry point).
- **Web UI**: simple static HTML/JS served by FastAPI.
- **Retrieval store**: SQLite with FTS5 (structured metadata + search documents).
- **Snapshots**: local versioned snapshot directory for raw fetched source HTML.
- **Schemas**: Pydantic.
- **Parsing**: `httpx` + `beautifulsoup4` (or stdlib `html.parser`) for catalog/department pages.
- **Tests**: pytest.

## Constitution Check

| Principle | Implementation alignment |
|---|---|
| Source-Grounded Academic Accuracy | Retrieval nodes are deterministic SQLite/FTS lookups over approved snapshots; the LLM answer node is constrained to restate retrieved facts. |
| Citation and Traceability by Default | `Citation` records with source document, evidence, snapshot, retrieved/index timestamps flow through graph state into the answer. |
| Structured Retrieval Before Open-Ended Web Search | Only structured retrieval tools are wired into the graph; no open-web tool exists in the default v1 graph. |
| Freshness and Temporal Awareness | Sources/citations/answers carry `snapshot_id`, `retrieved_at`, `indexed_at`. |
| Privacy and Student Data Protection | No auth, no student records; sensitive input is redacted before state/log persistence. |
| Robustness Against Stale, Conflicting, or Missing Data | Source tiers and conflict detection prevent silent overwrites; missing fields become limitation messages. |
| Persistent and Explicit Workflow State | `CourseResearchState` is checkpointed by `SqliteSaver` per `workflow_id`, resumable and inspectable. |
| Major Feature Testability and Validation | pytest unit tests for parsers/retrieval/routing; golden validation cases; graph integration tests. |
| Ethical Automation Boundaries | Read-only; no enrollment/registration/private UW access; see [runtime synthesis limitations](../../README.md#model-mode). |

No constitution violations identified.

## Target Architecture

```text
Web UI / API clients
  -> FastAPI
      -> LangGraph CourseResearchGraph
          -> Query Understanding (quick LLM, structured intent)
          -> ConditionalLogic router
              -> ExactCodeRetriever   (SQLite exact lookup)
              -> DepartmentRetriever  (SQLite department search)
              -> KeywordRetriever     (FTS keyword search)
              -> NLRetriever          (FTS natural-language search)
              -> Clarifier            (quick LLM follow-up question)
              -> OutOfScopeResponder  (limitation message)
          -> Answer Composer (deep LLM, grounded synthesis)
          -> Grounding Verifier (reject uncited claims)
          -> END
      -> SqliteSaver checkpointer (per workflow_id)

Manual Ingestion CLI (Typer)
  -> config/sources.yml
  -> Source Fetcher -> Snapshot Store -> Parser/Normalizer -> SQLite + FTS5
```

## Module Layout

```text
courseagent/
  agents/
    __init__.py
    state.py                 # CourseResearchState (MessagesState TypedDict)
    schemas.py               # Pydantic: QueryIntent, CourseAnswer, Citation, CourseSearchResult
    structured.py            # render helpers (structured -> markdown)
    query_understanding.py   # quick-tier intent classifier node
    retrievers.py            # deterministic retrieval nodes
    answer_composer.py       # deep-tier grounded synthesis node
    grounding.py             # uncited-claim verifier node
    clarifier.py             # ambiguity / out-of-scope responder nodes
  graph/
    __init__.py
    setup.py                 # StateGraph construction
    conditional_logic.py     # deterministic query router
    checkpointer.py          # SqliteSaver wrapper + thread_id helpers
    course_graph.py          # CourseResearchGraph orchestration class
  dataflows/
    __init__.py
    source_registry.py       # config/sources.yml loader + allowlist checks
    fetcher.py               # approved-source fetching
    snapshot_store.py        # raw snapshot persistence
    parsers/
      __init__.py
      uw_course_catalog.py
      department_page.py
    normalizer.py
    db.py                    # sqlite3 connection + schema (FTS5)
    indexer.py
    retrieval.py             # exact/department/keyword/natural-language search
  llm_clients/
    __init__.py
    factory.py               # deep/quick tier clients, DeepSeek default
  api/
    __init__.py
    app.py                   # FastAPI app + static web UI
    routes/
      search.py
      courses.py
      workflows.py
      admin.py
    schemas.py               # API request/response models
  web/
    index.html
    app.js
    styles.css
  cli/
    __init__.py
    main.py                  # Typer: ingest, search, serve
config/
  default_config.py
pyproject.toml
tests/
  ...
validation/
  golden-cases.json
  run_validation.py
```

The exact filenames may change, but the boundaries (agents, graph, dataflows, llm_clients, api, cli, web) must be preserved.

## Graph Design

### `CourseResearchState` (core fields)

```python
class CourseResearchState(MessagesState):
    query: Annotated[str, "User's course search query"]
    intent: Annotated[str, "Classified query intent"]
    interpreted_filters: Annotated[dict, "Parsed filters: campus/department/level/quarter"]
    retrieved_courses: Annotated[list, "Courses returned by retrieval"]
    citations: Annotated[list, "Citations for substantive facts"]
    freshness: Annotated[dict, "Freshness metadata"]
    answer: Annotated[str, "Final grounded answer"]
    structured_answer: Annotated[dict, "Structured CourseAnswer"]
    limitations: Annotated[list, "Limitation messages"]
    conflicts: Annotated[list, "Detected conflicts"]
    needs_clarification: Annotated[str, "Clarification question if ambiguous"]
    status: Annotated[str, "Workflow status"]
```

### Nodes and edges

```text
START
  -> "Query Understanding"       (quick LLM -> QueryIntent structured output)
  -> ConditionalLogic.route(state) -> one of:
       exact_code | department | keyword | natural_language | ambiguous | out_of_scope
  -> Retriever node for the intent   (deterministic SQLite/FTS; fills retrieved_courses/citations/freshness)
  -> "Answer Composer"               (deep LLM, grounded synthesis from retrieved facts)
  -> "Grounding Verifier"            (deterministic; rejects/limits uncited substantive claims)
  -> END

"Clarifier"         -> END (asks a follow-up question)
"OutOfScopeResponder" -> END (limitation message)
```

### Grounding rule (critical invariant)

The Answer Composer receives retrieved courses + citations as its only factual context and is instructed to:

- Answer only from the provided retrieved facts.
- Attach the provided citation for each substantive claim.
- Emit an explicit limitation when a fact is unavailable.
- Never assert live enrollment, seats, registration status, or schedule.

For the implemented catalog-answer contract and synthesis limitations, see
[README: Model mode](../../README.md#model-mode). The Grounding
Verifier adds limitations for retrieved courses without citations; it does not
verify generated prose (see `courseagent/agents/grounding.py`).

## Implementation Phases

### Phase 1: Project scaffolding

- Create `pyproject.toml` with LangGraph/FastAPI/Typer/pytest dependencies.
- Create `courseagent` package skeleton and `config/default_config.py`.
- Add `.gitignore` and shared domain schemas (`agents/schemas.py`, `agents/state.py`).

### Phase 2: Dataflows (snapshot retrieval backbone)

- Implement `source_registry.py` loading `config/sources.yml` with allowlist checks.
- Implement `fetcher.py` + `snapshot_store.py`.
- Implement catalog/department parsers + `normalizer.py`.
- Implement `db.py` (SQLite + FTS5 schema), `indexer.py`, `retrieval.py`.
- Implement `cli/main.py` ingest command.

### Phase 3: LLM clients + query understanding

- Implement `llm_clients/factory.py` (deep/quick tiers, DeepSeek default).
- Implement `query_understanding.py` returning `QueryIntent`.
- Implement `graph/conditional_logic.py` router.

### Phase 4: Graph assembly (US1 exact lookup first)

- Implement `retrievers.py` exact-code node.
- Implement `answer_composer.py` grounded synthesis.
- Implement `grounding.py` verifier.
- Implement `graph/setup.py` + `graph/course_graph.py` + `graph/checkpointer.py`.
- Wire the full graph for exact-code intent and add integration tests.

### Phase 5: Search intents (US2 + US3)

- Add department, keyword, and natural-language retrieval nodes.
- Extend router and answer composer for ranked-course responses.
- Add tests for ranking and NL discovery.

### Phase 6: Robustness intents (US4–US8)

- Prerequisites/quarter-availability handling.
- Out-of-scope and ambiguous responders.
- Conflict detection and privacy redaction.

### Phase 7: API + Web UI

- Implement FastAPI routes (`search`, `courses`, `workflows`, `admin`).
- Serve static web UI; implement search/detail/citation/limitation views.

### Phase 8: Validation & release readiness

- Add golden cases and `validation/run_validation.py`.
- Wire pytest suite and document quickstart.
- Run validation and record results.

## Key Decisions

| Decision | Rationale | Alternative considered |
|---|---|---|
| Python + LangGraph | Matches TradingAgents reference; `SqliteSaver` checkpointer natively satisfies persistent workflow state. | TypeScript + Fastify (earlier plan), dropped for agentic orchestration. |
| DeepSeek default LLM | User selection; OpenAI-compatible endpoint; TradingAgents already supports it. | OpenAI/Anthropic, kept behind provider factory. |
| Grounded synthesis only | Constitution requires source-grounded accuracy; prevents hallucinated course facts. | Free-form LLM answers, rejected as unsafe. |
| Deterministic retrieval nodes | Course search retrieval is structured lookup, not reasoning; more testable. | LLM tool-calling loops, unnecessary for v1 retrieval. |
| SQLite + FTS5 retrieval store | Small CSE/INFO corpus, local reproducibility. | Postgres/OpenSearch, deferred. |
| Manual ingestion CLI | Matches no-live-data + manual-refresh policy. | Scheduled refresh, deferred to post-v1. |

## Gates Before Implementation

- `config/sources.yml` validates and contains only approved sources.
- Grounding rule is encoded in Answer Composer prompt + Verifier logic.
- Exact-lookup vertical slice runs end-to-end through the graph with checkpointing.
- Golden validation cases for exact lookup, search, NL, missing/live-only, conflicts, and state persistence are defined.

## Generated Design Artifacts

- `specs/001-course-search/research.md`
- `specs/001-course-search/data-model.md`
- `specs/001-course-search/contracts/openapi.yaml`
- `specs/001-course-search/contracts/ui-contract.md`
- `specs/001-course-search/quickstart.md`
- `specs/001-course-search/tasks.md`
