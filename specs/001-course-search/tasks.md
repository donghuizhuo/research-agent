# Tasks: MVP UW Course Search

**Feature**: `001-course-search`  
**Input**: Implementation plan, spec, data model, contracts, and quickstart under `specs/001-course-search/`.

**Stack decisions** (from `research.md` and `plan.md`):

- TypeScript full-stack.
- Node.js + Fastify API.
- SQLite via `better-sqlite3` with FTS5 for structured storage and full-text search.
- React + Vite for the simple Web UI.
- `vitest` for tests.
- Manual ingestion CLI driven by `config/sources.yml`.

**Organization**: Tasks are grouped by user story (US) mapped from spec acceptance scenarios, with setup/foundational phases first and a final polish phase.

---

## Phase 1: Setup

**Goal**: Initialize the TypeScript project with the chosen runtime, tooling, and scripts.

- [ ] T001 Create root `package.json` with `type: "module"`, dependencies (`fastify`, `better-sqlite3`, `zod`), dev dependencies (`typescript`, `vitest`, `tsx`, `@types/node`, `@types/better-sqlite3`), and scripts `dev:api`, `dev:web`, `db:init`, `sources:validate`, `ingest`, `test`, `validate` in `package.json`
- [ ] T002 [P] Create `tsconfig.json` with strict mode, `ES2022` target, `NodeNext` module resolution, and `src/` root in `tsconfig.json`
- [ ] T003 [P] Create `vitest.config.ts` pointing at `src/**/*.test.ts` in `vitest.config.ts`
- [ ] T004 [P] Create `.gitignore` excluding `node_modules/`, `dist/`, `data/`, `.env`, and snapshot output directories in `.gitignore`
- [ ] T005 [P] Create `src/types/domain.ts` with shared TypeScript interfaces for `Course`, `CourseSource`, `Citation`, `FreshnessMetadata`, `WorkflowState`, `SearchResult`, and `SearchQuery` matching `specs/001-course-search/data-model.md` in `src/types/domain.ts`

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Implement shared infrastructure every user story depends on: source registry validation, database schema, snapshot storage, workflow state, and citation/freshness primitives.

- [ ] T006 Implement `loadSourceRegistry()` that parses `config/sources.yml` and returns typed registry entries with `id`, `tier`, `type`, `authority`, `department`, `url`, `allowed_url_patterns`, `extraction_policy`, and `freshness` in `src/ingest/source-registry.ts`
- [ ] T007 [P] Implement `isUrlApproved(url, registry)` that returns the matching registry entry or `null` if the URL matches no `allowed_url_patterns` in `src/ingest/source-registry.ts`
- [ ] T008 [P] Write SQLite schema in `src/db/schema.sql` creating tables `sources`, `snapshots`, `source_documents`, `courses`, `search_documents`, `citations`, `conflicts`, `workflow_state`, plus FTS5 virtual table `search_documents_fts(title, body, content='search_documents', content_rowid='rowid')` in `src/db/schema.sql`
- [ ] T009 Implement `openDatabase()` and `initSchema()` using `better-sqlite3` to create/load the database file under `data/app.db` and apply `src/db/schema.sql` in `src/db/db.ts`
- [ ] T010 [P] Implement `SnapshotStore` that writes fetched raw content to a versioned snapshot directory `data/snapshots/{snapshot_id}/{source_id}.html` and records content hash and `retrieved_at` in `src/ingest/snapshot-store.ts`
- [ ] T011 [P] Implement `createWorkflowState(db, input)` and `getWorkflowState(db, workflowId)` persisting `active_query`, `interpreted_filters`, `selected_courses`, `retrieved_source_ids`, `citation_ids`, `freshness_metadata`, `unresolved_uncertainty`, `limitations`, `status`, and `updated_at` in `src/core/workflow-state.ts`
- [ ] T012 [P] Implement `buildCitation(sourceDoc, claimField, evidenceText)` and `freshnessFromSource(sourceDoc)` producing `Citation` and `FreshnessMetadata` records that include `snapshot_id`, `retrieved_at`, and `indexed_at` when available in `src/core/citations.ts`
- [ ] T013 Write tests for source registry: approved URL matches, unregistered URL rejected, tier/extraction policy parsing from `config/sources.yml` in `src/ingest/source-registry.test.ts`

---

## Phase 3: US1 — Exact course-code lookup (P1)

**Goal**: A user can look up a specific UW Seattle course by course code and receive source-grounded facts with citations and freshness metadata.

**Independent test**: After manual ingestion of the CSE catalog, `POST /course-search` with `{"query":"CSE 142","mode":"exact_code"}` returns a course with citations and freshness; `GET /courses/CSE-142` returns detail fields.

- [ ] T014 [US1] Implement `fetchApprovedSources(registry, snapshotId, sourceIds?)` that fetches each approved source URL and writes raw HTML via `SnapshotStore` in `src/ingest/fetcher.ts`
- [ ] T015 [US1] Implement `parseUwCourseCatalog(html, sourceDoc)` that extracts department code, course number, title, description, and credits into normalized `Course` records with field-level provenance for the UW catalog page structure in `src/ingest/parsers/uw-course-catalog.ts`
- [ ] T016 [US1] Implement `normalizeCourses(parsed)` that enforces `course_id = {DEPARTMENT}-{NUMBER}`, campus `seattle`, and Tier 1 normalized-fact policy in `src/ingest/normalizer.ts`
- [ ] T017 [US1] Implement `indexCourses(db, courses, snapshotId)` that upserts normalized courses and writes citations from field provenance into `courses` and `citations` tables in `src/ingest/indexer.ts`
- [ ] T018 [US1] Implement `ingestSnapshot(sourceIds?)` orchestration in the ingestion CLI: create snapshot record, fetch, parse, normalize, index, and set snapshot `status` to `indexed` in `src/ingest/cli.ts`
- [ ] T019 [US1] Implement exact course lookup `findCourseByCode(db, department, number)` with SQL matching `course_id` or `department_code + course_number` in `src/core/retrieval.ts`
- [ ] T020 [US1] Implement `composeCourseAnswer(course, citations, freshness)` that returns title, department, course number, description, credits and attaches citations/freshness while emitting `limitations` for unavailable fields in `src/core/answer-composer.ts`
- [ ] T021 [US1] Implement `POST /course-search` route that parses `query`/`mode`, routes exact-code queries to `findCourseByCode`, composes the answer, creates/updates `WorkflowState`, and returns `CourseSearchResponse` in `src/api/routes/course-search.ts`
- [ ] T022 [US1] Implement `GET /courses/{course_id}` route returning `CourseDetailResponse` with per-field citations and limitations in `src/api/routes/courses.ts`
- [ ] T023 [US1] Implement `GET /workflows/{workflow_id}` route returning persisted `WorkflowState` in `src/api/routes/workflows.ts`
- [ ] T024 [US1] Implement Fastify server assembly registering routes and JSON schema validation in `src/api/server.ts`
- [ ] T025 [US1] Write tests for exact course-code retrieval and answer composition using a fixture CSE catalog HTML in `src/core/retrieval.test.ts` and `src/core/answer-composer.test.ts`
- [ ] T026 [US1] Write an API integration test that seeds a minimal DB and asserts exact lookup response includes citation and freshness in `src/api/routes/course-search.test.ts`

---

## Phase 4: US2 — Department & keyword search (P1)

**Goal**: A user can search by department or keyword and receive a ranked list of relevant courses.

**Independent test**: `POST /course-search` with `{"query":"CSE","mode":"department","filters":{"department":"CSE"}}` returns ranked CSE results with citations.

- [ ] T027 [US2] Extend `src/ingest/indexer.ts` to write each course title, description, and prerequisites into `search_documents` and the FTS5 table with `document_type = 'course_record'` in `src/ingest/indexer.ts`
- [ ] T028 [US2] Implement `searchCourses(db, query, filters)` using FTS5 `MATCH` for keyword queries and `department_code` filtering, returning ranked rows with relevance scores in `src/core/retrieval.ts`
- [ ] T029 [US2] Implement department abbreviation parsing in `interpretQuery()` that maps department terms and detects `department`/`keyword`/`exact_code` intent in `src/core/query-understanding.ts`
- [ ] T030 [US2] Extend `composeCourseAnswer` path to compose a `ranked_courses` response with concise per-course summaries and citation links in `src/core/answer-composer.ts`
- [ ] T031 [US2] Wire department/keyword modes into `POST /course-search` route and persist retrieved source/citation IDs to `WorkflowState` in `src/api/routes/course-search.ts`
- [ ] T032 [US2] Write tests for department and keyword search returning at least one relevant result in the top five using fixture course data in `src/core/retrieval.test.ts`

---

## Phase 5: US3 — Natural-language course discovery (P1)

**Goal**: A user can ask a natural-language course discovery question and get ranked relevant courses without personalized advising.

**Independent test**: `POST /course-search` with `{"query":"intro programming courses","mode":"natural_language"}` returns relevant indexed courses and limitations; no advising claims are produced.

- [ ] T033 [US3] Implement query normalization for natural-language input: lowercase, strip stopwords, extract department/code/level hints into `interpreted_filters` in `src/core/query-understanding.ts`
- [ ] T034 [US3] Implement natural-language retrieval path that converts the normalized query into an FTS5 query over `search_documents_fts` and ranks results in `src/core/retrieval.ts`
- [ ] T035 [US3] Add department-page context chunks to `search_documents` with `document_type = 'department_context'` via a `chunkDepartmentPage(html)` helper in `src/ingest/parsers/department-page.ts`
- [ ] T036 [US3] Implement `composeNaturalLanguageAnswer()` that returns `ranked_courses`, attaches `limitations` for snapshot-only/no-live-data behavior, and refuses advising-style claims in `src/core/answer-composer.ts`
- [ ] T037 [US3] Wire `natural_language` mode into the search route and persist limitations/unresolved uncertainty to `WorkflowState` in `src/api/routes/course-search.ts`
- [ ] T038 [US3] Write tests for natural-language query normalization and retrieval relevance using fixture search documents in `src/core/query-understanding.test.ts` and `src/core/retrieval.test.ts`

---

## Phase 6: US4 + US5 — Prerequisites and quarter availability (P2)

**Goal**: The system returns prerequisites/corequisites only when source-supported and never claims quarter-specific offering without snapshot confirmation.

**Independent test**: A course with prerequisites in the catalog returns them with citations; a course without them returns "unavailable" rather than inferred; a quarter question returns availability only when snapshot data confirms it.

- [ ] T039 [US4] Extend `parseUwCourseCatalog` to extract prerequisites and corequisites into normalized `Course` fields with provenance in `src/ingest/parsers/uw-course-catalog.ts`
- [ ] T040 [US4] Extend `composeCourseAnswer` to return prerequisite/corequisite facts only when cited and emit a limitation when unavailable in `src/core/answer-composer.ts`
- [ ] T041 [US5] Implement `hasQuarterConfirmation(course, quarter)` that returns true only when a cited snapshot source confirms that quarter; otherwise returns false in `src/core/freshness.ts`
- [ ] T042 [US5] Extend the search/detail response to answer quarter questions only from confirmed snapshot data and return a live-only limitation otherwise in `src/core/answer-composer.ts`
- [ ] T043 [US4] Write tests for prerequisite extraction and unavailable-prerequisite messaging in `src/ingest/parsers/uw-course-catalog.test.ts` and `src/core/answer-composer.test.ts`
- [ ] T044 [US5] Write tests that quarter offering is never confirmed when snapshot lacks that quarter in `src/core/freshness.test.ts`

---

## Phase 7: US6 + US7 + US8 — Web fallback labeling, conflicts, and privacy (P2)

**Goal**: The system labels web-search answers, surfaces conflicts, and avoids sensitive student data.

**Independent test**: Structured-miss queries do not present generic web results as facts; conflicting sources produce a conflict summary; sensitive inputs are not stored.

- [ ] T045 [US6] Implement `composeFallbackAnswer()` that returns a labeled limitation instead of authoritative facts when structured retrieval misses and open-ended web search is not justified in `src/core/answer-composer.ts`
- [ ] T046 [US7] Implement `detectConflicts(db, courseId, field)` that compares cited values across sources and returns `Conflict` records rather than silently choosing one in `src/core/citations.ts`
- [ ] T047 [US7] Add `conflicts` array to the course detail and search responses when material conflicts exist in `src/core/answer-composer.ts`
- [ ] T048 [US8] Implement `redactSensitiveInput(query)` that strips obvious student identifiers (ID numbers, NetID-like tokens) before logging or storing in `src/core/privacy.ts`
- [ ] T049 [US8] Apply `redactSensitiveInput` in the search route before persisting workflow state and reject requests that require private student data in `src/api/routes/course-search.ts`
- [ ] T050 [US7] Write tests for conflict detection and conflict surfacing in `src/core/citations.test.ts` and `src/core/answer-composer.test.ts`
- [ ] T051 [US8] Write tests for sensitive-input redaction and non-persistence in `src/core/privacy.test.ts`

---

## Phase 8: Web UI (P1 surface)

**Goal**: A simple browser UI exposes exact lookup, department/keyword search, natural-language search, citations, freshness, and workflow-state-backed follow-ups.

**Independent test**: Manual UI check confirms all six `ui-contract.md` validation scenarios.

- [ ] T052 [US1] Scaffold Vite + React + TypeScript web app under `src/web/` with an `index.html` and dev server wiring in `src/web/`
- [ ] T053 [P] [US1] Implement `SearchBox` component that submits queries and preserves `workflow_id` in `src/web/components/SearchBox.tsx`
- [ ] T054 [P] [US1] Implement `ResultsList` component that renders ranked results with course ID, title, credits, and citation count in `src/web/components/ResultsList.tsx`
- [ ] T055 [P] [US1] Implement `CourseDetail` component that calls `GET /courses/{id}` and renders fields with unavailable-placeholder handling in `src/web/components/CourseDetail.tsx`
- [ ] T056 [P] [US1] Implement `CitationPanel` component showing source title, URL, evidence, snapshot ID, and timestamps in `src/web/components/CitationPanel.tsx`
- [ ] T057 [P] [US1] Implement `LimitationBanner` component showing snapshot-only/no-live-data messaging and contextual limitations in `src/web/components/LimitationBanner.tsx`
- [ ] T058 [US1] Implement `App.tsx` composing SearchBox, ResultsList, CourseDetail, CitationPanel, and LimitationBanner with a shared API client in `src/web/App.tsx`
- [ ] T059 [US1] Add a minimal UI validation checklist mapping to `contracts/ui-contract.md` scenarios in `src/web/UI_VALIDATION.md`

---

## Phase 9: Polish & cross-cutting concerns

**Goal**: Add golden validation cases, end-to-end validation, and release readiness documentation.

- [ ] T060 Implement `validation/golden-cases.json` with CSE/INFO exact-lookup, department, keyword, natural-language, missing-field, live-only, conflict, and workflow-state cases in `validation/golden-cases.json`
- [ ] T061 Implement `validation/run-validation.ts` that loads `validation/golden-cases.json` and runs the API/retrieval paths, reporting pass/fail in `validation/run-validation.ts`
- [ ] T062 Implement `src/api/routes/admin.ts` exposing restricted `POST /admin/snapshots/import` that calls `ingestSnapshot` with approved source IDs only in `src/api/routes/admin.ts`
- [ ] T063 Wire `npm run sources:validate`, `npm run db:init`, `npm run ingest`, `npm run dev:api`, `npm run dev:web`, `npm test`, and `npm run validate` scripts to the implemented modules in `package.json`
- [ ] T064 Update `specs/001-course-search/quickstart.md` to match any final command names and confirm each documented step is runnable in `specs/001-course-search/quickstart.md`
- [ ] T065 Run `npm test` and `npm run validate`, fix failures, and record a passing validation run result in `.agent-state.md`

---

## Dependencies

- US1 (Phase 3) depends on Foundational (Phase 2).
- US2 (Phase 4) depends on US1 ingestion/indexing.
- US3 (Phase 5) depends on US2 FTS indexing and query understanding.
- US4/US5 (Phase 6) depend on US1 parser and answer composer.
- US6/US7/US8 (Phase 7) depend on US1 answer composer and citations.
- Web UI (Phase 8) depends on the API routes from US1–US3.
- Polish (Phase 9) depends on all prior phases.

## Parallel execution opportunities

- Within Phase 1: T002, T003, T004, T005 can run in parallel.
- Within Phase 2: T007, T008, T010, T011, T012 can run in parallel after T006/T009.
- Within Phase 8: T053–T057 can run in parallel after T052.

## Suggested MVP scope

Ship the minimum: Phase 1 → Phase 2 → Phase 3 (US1 exact lookup) as the first vertical slice, then add US2/US3 search, then the Web UI.
