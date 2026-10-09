# Tasks: MVP UW Course Search (LangGraph)

**Feature**: `001-course-search`  
**Input**: `plan.md`, `spec.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`.

**Stack**: Python 3.11+, LangGraph, FastAPI, Typer, DeepSeek (OpenAI-compatible), SQLite + FTS5, pytest.

**Organization**: Setup → Foundational dataflows → LLM/query understanding → graph assembly by user story → API/Web UI → validation.

---

## Phase 1: Setup

**Goal**: Initialize the Python project with LangGraph/FastAPI/Typer tooling and shared domain types.

- [x] T001 Create `pyproject.toml` with dependencies (`langgraph`, `langchain-core`, `langchain-openai`, `langgraph-checkpoint-sqlite`, `fastapi`, `uvicorn`, `typer`, `pydantic`, `httpx`, `beautifulsoup4`, `python-dotenv`, `rich`) and dev dependencies (`pytest`, `pytest-subtests`), plus `[project.scripts] courseagent = "courseagent.cli.main:app"` in `pyproject.toml`
- [x] T002 [P] Create `config/default_config.py` with defaults for `data_dir`, `snapshots_dir`, `db_path`, `sources_path`, `llm_provider`, `quick_model`, `deep_model`, `deepseek_base_url`, and `max_tool_rounds` in `config/default_config.py`
- [x] T003 [P] Create `.gitignore` excluding `__pycache__/`, `.venv/`, `dist/`, `data/`, `.env`, and snapshot output directories in `.gitignore`
- [x] T004 [P] Create package skeleton `__init__.py` files under `courseagent/`, `courseagent/agents/`, `courseagent/graph/`, `courseagent/dataflows/`, `courseagent/llm_clients/`, `courseagent/api/`, `courseagent/cli/` in `courseagent/`
- [x] T005 [P] Implement `CourseResearchState(MessagesState)` in `courseagent/agents/state.py` with annotated fields `query`, `intent`, `interpreted_filters`, `retrieved_courses`, `citations`, `freshness`, `answer`, `structured_answer`, `limitations`, `conflicts`, `needs_clarification`, `status` in `courseagent/agents/state.py`
- [x] T006 [P] Implement Pydantic schemas `QueryIntent`, `CourseAnswer`, `Citation`, `FreshnessMetadata`, `CourseSearchResult`, and `render_*` helpers in `courseagent/agents/schemas.py`

---

## Phase 2: Foundational dataflows (blocking prerequisites)

**Goal**: Implement the snapshot retrieval backbone: source registry, snapshot storage, parsers, and SQLite/FTS retrieval store.

- [x] T007 Implement `load_source_registry(path)` and `is_url_approved(url, registry)` that parse `config/sources.yml` and match URLs against `allowed_url_patterns` in `courseagent/dataflows/source_registry.py`
- [x] T008 [P] Implement `open_db(path)` and `init_schema(conn)` creating tables `sources`, `snapshots`, `source_documents`, `courses`, `search_documents`, `citations`, `conflicts`, plus FTS5 virtual table `search_documents_fts(title, body, content='search_documents')` in `courseagent/dataflows/db.py`
- [x] T009 [P] Implement `SnapshotStore` writing raw content to `data/snapshots/{snapshot_id}/{source_id}.html` with content hash and `retrieved_at` in `courseagent/dataflows/snapshot_store.py`
- [x] T010 Implement `fetch_approved_sources(registry, snapshot_id, source_ids?)` using `httpx` that fetches only approved URLs and writes snapshots in `courseagent/dataflows/fetcher.py`
- [x] T011 [P] Implement `parse_uw_course_catalog(html, source_doc)` extracting department code, course number, title, description, credits, prerequisites, corequisites with field provenance in `courseagent/dataflows/parsers/uw_course_catalog.py`
- [x] T012 [P] Implement `chunk_department_page(html)` producing searchable department-context chunks without promoting them to normalized facts in `courseagent/dataflows/parsers/department_page.py`
- [x] T013 Implement `normalize_courses(parsed)` enforcing `course_id = {DEPARTMENT}-{NUMBER}`, campus `seattle`, and Tier 1 fact policy in `courseagent/dataflows/normalizer.py`
- [x] T014 Implement `index_courses(db, courses, snapshot_id)` upserting courses, search documents, and citations from field provenance in `courseagent/dataflows/indexer.py`
- [x] T015 [P] Implement `find_course_by_code`, `search_department`, `search_keyword`, `search_natural_language` over SQLite/FTS5 in `courseagent/dataflows/retrieval.py`
- [x] T016 Implement `ingest` Typer command that creates a snapshot record, fetches, parses, normalizes, indexes, and sets snapshot `status` to `indexed` in `courseagent/cli/main.py`
- [x] T017 Write tests for source registry allowlist checks and catalog parsing using fixture HTML in `tests/test_source_registry.py` and `tests/test_catalog_parser.py`

---

## Phase 3: LLM clients + query understanding

**Goal**: Provide tiered LLM clients and the structured query-intent classifier that drives graph routing.

- [x] T018 Implement `create_tier_client(config, tier)` returning DeepSeek `ChatOpenAI` clients (custom `base_url`) for `deep`/`quick` tiers with OpenAI-compatible fallback in `courseagent/llm_clients/factory.py`
- [x] T019 Implement `classify_query(query, llm)` returning a `QueryIntent` structured output (intent enum + parsed filters) in `courseagent/agents/query_understanding.py`
- [x] T020 Implement `ConditionalLogic.route(state)` returning `exact_code | department | keyword | natural_language | ambiguous | out_of_scope` based on `state["intent"]` in `courseagent/graph/conditional_logic.py`
- [x] T021 Write tests for `QueryIntent` classification and router behavior using a stub LLM in `tests/test_query_understanding.py` and `tests/test_conditional_logic.py`

---

## Phase 4: US1 — Exact course-code lookup graph (P1)

**Goal**: A user can look up a specific course and receive a grounded answer with citations, freshness, and resumable workflow state.

**Independent test**: After manual ingestion of the CSE catalog, invoking the graph with `{"query":"CSE 142","intent":"exact_code"}` returns an answer with citation and freshness, checkpointed under a `workflow_id`.

- [x] T022 [US1] Implement `exact_code_retriever(state)` node that calls `find_course_by_code` and populates `retrieved_courses`, `citations`, and `freshness` in `courseagent/agents/retrievers.py`
- [x] T023 [US1] Implement `compose_answer(state)` in `courseagent/agents/answer_composer.py`; see the [catalog answer and optional synthesis contract](../../README.md#optional-model-mode).
- [x] T024 [US1] Implement `verify_grounding(state)` in `courseagent/agents/grounding.py`; see [verification limits](../../README.md#optional-model-mode).
- [x] T025 [US1] Implement `setup_graph()` building the `StateGraph` with `START -> Query Understanding -> conditional -> retriever -> Answer Composer -> Grounding Verifier -> END` in `courseagent/graph/setup.py`
- [x] T026 [US1] Implement `SqliteSaver` wrapper `get_checkpointer(data_dir, workflow_id)` and deterministic `thread_id` helper in `courseagent/graph/checkpointer.py`
- [x] T027 [US1] Implement `CourseResearchGraph` orchestration class with `run(query, workflow_id)` that compiles with the checkpointer and invokes/streams the graph in `courseagent/graph/course_graph.py`
- [x] T028 [US1] Write graph integration test seeding a minimal DB and asserting exact lookup returns cited, fresh, checkpointed answer in `tests/test_course_graph_us1.py`

---

## Phase 5: US2 + US3 — Department, keyword, and natural-language search (P1)

**Goal**: Users can search by department, keyword, or natural-language discovery and receive ranked, cited results.

**Independent test**: `department`/`keyword`/`natural_language` intents return ranked results with citations and snapshot-only limitations.

- [x] T029 [US2] Implement `department_retriever` and `keyword_retriever` nodes in `courseagent/agents/retrievers.py` using `search_department` and `search_keyword` in `courseagent/agents/retrievers.py`
- [x] T030 [US3] Implement `natural_language_retriever` node using `search_natural_language` over FTS5 in `courseagent/agents/retrievers.py`
- [x] T031 [US2] Extend `compose_answer` to produce `ranked_courses` responses with concise per-course summaries and citation links in `courseagent/agents/answer_composer.py`
- [x] T032 [US2] Extend `setup_graph` to wire department/keyword/natural-language retriever nodes into the conditional router in `courseagent/graph/setup.py`
- [x] T033 [US2] Write tests for department/keyword ranking and natural-language discovery using fixture search documents in `tests/test_retrievers.py`

---

## Phase 6: US4–US8 — Prerequisites, availability, conflicts, privacy (P2)

**Goal**: Handle prerequisites/quarter availability conservatively, surface conflicts, and protect sensitive data.

**Independent test**: Prerequisites return only when cited; quarter offering is never confirmed without snapshot data; conflicts are surfaced; sensitive input is redacted.

- [x] T034 [US4] Ensure `compose_answer` returns prerequisite/corequisite facts only when cited and emits a limitation otherwise in `courseagent/agents/answer_composer.py`
- [x] T035 [US5] Implement `has_quarter_confirmation(course, quarter)` and wire quarter-availability limitations into answers in `courseagent/agents/grounding.py`
- [x] T036 [US6] Implement `out_of_scope_responder` node returning a labeled limitation instead of authoritative facts when structured retrieval misses in `courseagent/agents/clarifier.py`
- [x] T037 [US6] Implement `clarifier` node producing a follow-up `needs_clarification` question for ambiguous queries in `courseagent/agents/clarifier.py`
- [x] T038 [US7] Implement `detect_conflicts(courses, citations)` comparing cited values across sources and populating `conflicts` in `courseagent/agents/grounding.py`
- [x] T039 [US8] Implement `redact_sensitive_input(query)` stripping student IDs/NetID-like tokens before state persistence/logging in `courseagent/agents/grounding.py`
- [x] T040 [US4] Write tests for prerequisites, quarter availability, conflict detection, and sensitive-input redaction in `tests/test_grounding.py` and `tests/test_privacy.py`

---

## Phase 7: API + Web UI (P1 surface)

**Goal**: Expose the agent through a FastAPI API and a simple browser UI with citations, freshness, and limitation display.

**Independent test**: API endpoints and the static UI complete exact lookup, department/keyword/NL search, course detail, and workflow inspection.

- [x] T041 Implement FastAPI app with `POST /course-search`, `GET /courses/{course_id}`, `GET /workflows/{workflow_id}`, and `POST /admin/snapshots/import` calling `CourseResearchGraph` in `courseagent/api/app.py`
- [x] T042 Implement API request/response Pydantic models matching `contracts/openapi.yaml` in `courseagent/api/schemas.py`
- [x] T043 [P] Implement `POST /course-search` route that builds `workflow_id`, runs the graph, and returns the structured answer with citations/freshness/limitations in `courseagent/api/routes/search.py`
- [x] T044 [P] Implement `GET /courses/{course_id}` route returning course detail with per-field citations in `courseagent/api/routes/courses.py`
- [x] T045 [P] Implement `GET /workflows/{workflow_id}` route reading checkpointed state in `courseagent/api/routes/workflows.py`
- [x] T046 [P] Implement `POST /admin/snapshots/import` route delegating to the ingest command with approved source IDs only in `courseagent/api/routes/admin.py`
- [x] T047 Implement `serve` Typer command starting uvicorn for the FastAPI app and static web UI in `courseagent/cli/main.py`
- [x] T048 [P] Implement static Web UI `index.html`, `app.js`, `styles.css` with search box, results list, course detail, citation panel, and limitation banner in `courseagent/web/`
- [x] T049 [P] Add UI validation checklist mapping to `contracts/ui-contract.md` scenarios in `courseagent/web/UI_VALIDATION.md`
- [x] T050 Write API integration tests asserting `POST /course-search` returns citation and freshness for a seeded course in `tests/test_api_search.py`

---

## Phase 8: Validation & release readiness

**Goal**: Add golden validation cases, wire the pytest suite, and confirm release readiness.

- [x] T051 Implement `validation/golden-cases.json` with CSE/INFO exact-lookup, department, keyword, natural-language, missing-field, live-only, conflict, and workflow-state cases in `validation/golden-cases.json`
- [x] T052 Implement `validation/run_validation.py` loading golden cases and running the graph/API paths, reporting pass/fail in `validation/run_validation.py`
- [x] T053 Update `specs/001-course-search/quickstart.md` to match final CLI/API commands and confirm each documented step is runnable in `specs/001-course-search/quickstart.md`
- [x] T054 Run `pytest` and `validation/run_validation.py`, fix failures, and record a passing validation run in `.agent-state.md`

---

## Dependencies

- US1 (Phase 4) depends on Foundational dataflows (Phase 2) and query understanding (Phase 3).
- US2/US3 (Phase 5) depend on US1 graph assembly.
- US4–US8 (Phase 6) depend on US1 answer composer/grounding nodes.
- API/Web UI (Phase 7) depend on the graph from US1–US3.
- Validation (Phase 8) depends on all prior phases.

## Parallel execution opportunities

- Phase 1: T002–T006 parallel after T001.
- Phase 2: T008, T009, T011, T012, T015 parallel after T007/T010/T013/T014.
- Phase 7: T043–T046 and T048–T049 parallel after T041/T042.

## Suggested MVP scope

Ship the minimum: Phase 1 → Phase 2 → Phase 3 → Phase 4 (US1 exact lookup through the full graph with checkpointing), then add US2/US3 search, then API/Web UI.
