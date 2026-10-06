# Implementation Plan: MVP UW Course Search

**Feature**: `001-course-search`  
**Spec**: `specs/001-course-search/spec.md`  
**High-level design**: `docs/design/course-search-high-level-design.md`  
**Source registry**: `config/sources.yml`  
**Status**: Draft implementation design  
**Date**: 2026-10-06

## Summary

Build a read-only UW Seattle course research MVP for CSE and INFO using approved indexed/snapshot sources. The first implementation should deliver a thin vertical slice from source ingestion to API and Web UI search results with citations, freshness metadata, and explicit workflow state.

## Technical Context

- **Application shape**: Full-stack web app with API and simple Web UI.
- **Recommended stack**: TypeScript for API, ingestion, and Web UI to keep contracts/types shared.
- **API runtime**: Node.js HTTP server, framework-agnostic in design; Fastify or Express are suitable.
- **Web UI**: React/Vite-style single-page UI or similarly simple browser app.
- **Persistence for MVP**: SQLite database with FTS5 for structured metadata, source/citation records, workflow state, and keyword search.
- **Natural-language search v1**: Query normalization + lexical/full-text search over normalized course fields and department-page chunks. Optional vector search may be added later behind the retrieval interface.
- **Snapshot storage**: Local versioned snapshot directory for raw fetched source HTML and ingestion outputs.
- **Source control**: `config/sources.yml` is the only approved ingestion allowlist.
- **Refresh cadence**: Manual refresh for MVP; scheduled refresh deferred but ingestion commands should be reusable.
- **Validation**: Unit tests for parsers/retrieval/state plus end-to-end validation cases through API and Web UI paths.

## Constitution Check

| Principle | Implementation alignment |
|---|---|
| Source-Grounded Academic Accuracy | Answers are generated only from indexed Course, CourseSource, and Citation records. Unsupported facts return limitations. |
| Citation and Traceability by Default | Data model stores field/source provenance and evidence snippets. API responses include citations for substantive facts. |
| Structured Retrieval Before Open-Ended Web Search | Retrieval uses SQLite/FTS index populated from `config/sources.yml`; no open web in default v1 path. |
| Freshness and Temporal Awareness | Snapshots, sources, citations, and answers carry `snapshot_id`, `retrieved_at`, and `indexed_at` when available. |
| Privacy and Student Data Protection | No auth, no student records, no sensitive information required; logs should redact obvious sensitive values. |
| Robustness Against Stale, Conflicting, or Missing Data | Source priority and conflict records prevent silent overwrites; missing fields produce user-facing limitations. |
| Persistent and Explicit Workflow State | Workflow state is persisted by `workflow_id` and returned/inspectable via API. |
| Major Feature Testability and Validation | Quickstart and validation cases cover exact lookup, search, NL discovery, citations, freshness, conflicts, and state. |
| Ethical Automation Boundaries | Read-only API/UI; no enrollment, registration, private UW access, or live availability checks. |

No constitution violations identified.

## Target Architecture

```text
Web UI
  -> Course Research API
      -> Query Understanding
      -> Retrieval Orchestrator
          -> SQLite Course Metadata Tables
          -> SQLite FTS Search Index
          -> Source/Citation Tables
      -> Answer Composer
      -> Workflow State Store

Manual Ingestion CLI
  -> config/sources.yml
  -> Source Fetcher
  -> Snapshot Store
  -> Parser/Normalizer
  -> SQLite Tables + FTS Index
```

## Module Breakdown

```text
src/
  api/
    server.ts
    routes/course-search.ts
    routes/courses.ts
    routes/workflows.ts
    schemas.ts
  core/
    answer-composer.ts
    citations.ts
    freshness.ts
    query-understanding.ts
    retrieval.ts
    source-policy.ts
    workflow-state.ts
  ingest/
    cli.ts
    source-registry.ts
    fetcher.ts
    snapshot-store.ts
    parsers/
      uw-course-catalog.ts
      department-page.ts
    normalizer.ts
    indexer.ts
  db/
    schema.sql
    migrations/
    repository.ts
  web/
    App.tsx
    components/
      SearchBox.tsx
      ResultsList.tsx
      CourseDetail.tsx
      CitationPanel.tsx
      LimitationBanner.tsx
  validation/
    golden-cases.json
    run-validation.ts
```

The exact filenames may change, but implementation should preserve these boundaries: API, core retrieval/answer logic, ingestion, persistence, Web UI, and validation.

## Implementation Phases

### Phase 1: Foundation and source registry

- Add project runtime/package files.
- Define shared TypeScript domain types.
- Load and validate `config/sources.yml`.
- Create database schema and local snapshot directory conventions.
- Add baseline tests for source-policy behavior.

### Phase 2: Manual ingestion vertical slice

- Fetch approved CSE/INFO catalog sources and department pages.
- Store raw HTML snapshots with `snapshot_id`, `retrieved_at`, and source ID.
- Parse UW course catalog pages into normalized Course records.
- Chunk department pages as supporting searchable context.
- Build SQLite tables and FTS index.
- Validate that unregistered URLs are rejected.

### Phase 3: Retrieval and answer composition

- Implement exact course-code lookup.
- Implement department and keyword search.
- Implement scoped natural-language discovery as normalized full-text search.
- Compose responses with citations, freshness, and limitation messages.
- Persist workflow state for every query.

### Phase 4: API

- Implement `POST /course-search`.
- Implement `GET /courses/{course_id}`.
- Implement `GET /workflows/{workflow_id}`.
- Implement restricted/manual `POST /admin/snapshots/import` or CLI equivalent.
- Add API contract tests.

### Phase 5: Web UI

- Implement simple search page.
- Implement ranked results list.
- Implement course detail view.
- Display citations, freshness, and no-live-data limitations.
- Preserve and pass `workflow_id` for follow-up queries.

### Phase 6: Validation and release readiness

- Add golden validation cases for CSE/INFO exact lookup, department search, keyword search, and natural-language discovery.
- Add missing/live-only/conflict test cases.
- Add quickstart validation flow.
- Run tests and document known limitations.

## Key Implementation Decisions

| Decision | Rationale | Alternative considered |
|---|---|---|
| TypeScript full-stack | Shared types across ingestion, API, and Web UI reduce contract drift. | Python API + JS UI, but it adds language boundary overhead for MVP. |
| SQLite + FTS5 | Fits small CSE/INFO MVP, simple local dev, supports structured tables and full-text search. | Postgres/OpenSearch, deferred until scale or deployment requires it. |
| Lexical NL search first | Meets scoped v1 NL discovery without embeddings complexity. | Vector search, deferred behind retrieval interface. |
| Manual ingestion CLI | Matches MVP refresh policy and simplifies operations. | Scheduler, deferred until post-v1. |
| Field/source provenance | Required for citations, conflict handling, and auditability. | Whole-record citations only, less precise and weaker validation. |

## Gates Before Implementation

- `config/sources.yml` validates and contains only approved sources.
- Data model and API contract are reviewed.
- Quickstart validation scenarios are documented.
- First implementation task targets a thin vertical slice: ingest one catalog source, exact lookup, citation, freshness, workflow state, and API response.

## Generated Design Artifacts

- `specs/001-course-search/research.md`
- `specs/001-course-search/data-model.md`
- `specs/001-course-search/contracts/openapi.yaml`
- `specs/001-course-search/contracts/ui-contract.md`
- `specs/001-course-search/quickstart.md`
