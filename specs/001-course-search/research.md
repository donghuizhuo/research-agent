# Research: MVP UW Course Search Implementation

## Decision: TypeScript full-stack for v1

**Rationale**: The MVP includes ingestion, API, and Web UI. TypeScript allows shared domain types and response schemas across all three surfaces, reducing drift between API contracts, UI rendering, and validation fixtures.

**Alternatives considered**:

- Python API/ingestion + JavaScript UI: strong parsing ecosystem but adds a cross-language boundary.
- Python-only CLI/API: simpler ingestion but weaker fit for Web UI.
- Full framework-first app: useful later, but early work benefits from explicit module boundaries.

## Decision: SQLite with FTS5 for MVP persistence/search

**Rationale**: The initial corpus is CSE and INFO sources, likely small enough for a single local database. SQLite supports structured records, workflow state, source/citation tables, and FTS5 for keyword/natural-language discovery without operating a separate search service.

**Alternatives considered**:

- PostgreSQL: stronger concurrent production story, but more setup for MVP.
- OpenSearch/Elasticsearch: powerful search, but operationally heavy for the first vertical slice.
- In-memory/index files only: simple, but weaker workflow persistence and validation reproducibility.

## Decision: Manual ingestion CLI first

**Rationale**: The spec says manual refresh for MVP and scheduled refresh later. A CLI/import command keeps ingestion reproducible while avoiding premature scheduling infrastructure.

**Alternatives considered**:

- Scheduled cron/job runner: useful post-v1 but not required yet.
- Live fetch during query: violates no-live-data and reproducibility constraints.

## Decision: Lexical full-text natural-language search first

**Rationale**: V1 natural-language search is scoped to retrieval and ranking over indexed/snapshot sources. Query normalization plus full-text search over title, description, prerequisites, and department-page chunks is enough for initial validation and keeps citations easier to reason about.

**Alternatives considered**:

- Embedding/vector search: may improve semantic recall, but introduces model dependencies, evaluation complexity, and possible precision/citation risks.
- LLM-only query answering: riskier for unsupported facts and harder to validate.

## Decision: Explicit source registry as ingestion allowlist

**Rationale**: `config/sources.yml` records approved sources, tiers, URL patterns, extraction policies, and freshness requirements. This prevents accidental broad crawling and keeps source coverage testable.

**Alternatives considered**:

- Hard-code URLs in ingestion code: less transparent and harder to audit.
- Crawl UW domains dynamically: too broad for v1 and weakens reproducibility.

## Decision: Strict department-page promotion policy

**Rationale**: Catalog/course-description sources own normalized facts. Department pages improve discovery and context but can only populate normalized facts when clearly structured and directly cited. This reduces extraction errors and source conflicts.

**Alternatives considered**:

- Treat department pages as equal fact sources: higher recall, but greater conflict and parsing risk.
- Never use department pages for facts: safest, but may miss useful structured department evidence.

## Decision: Field/source provenance in normalized records

**Rationale**: Citation and traceability are constitutional principles. Field-level provenance enables precise answers, conflict surfacing, and validation that facts came from approved sources.

**Alternatives considered**:

- Whole-course source citation only: simpler but less precise.
- Evidence-only without normalized fields: traceable but less efficient for exact lookup/filtering.
