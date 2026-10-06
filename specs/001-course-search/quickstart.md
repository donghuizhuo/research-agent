# Quickstart Validation: MVP UW Course Search

This guide defines the expected validation flow for the first implementation. Commands are illustrative until package scripts are added.

## Prerequisites

- Node.js runtime suitable for the chosen TypeScript toolchain.
- Network access for manual snapshot import of approved public sources.
- `config/sources.yml` present with the initial CSE/INFO source seed.

## Setup

```bash
npm install
npm run db:init
```

Expected outcome:

- Local database is created.
- Schema includes sources, snapshots, course records, search documents, citations, conflicts, and workflow state.

## Validate source registry

```bash
npm run sources:validate
```

Expected outcome:

- `config/sources.yml` loads successfully.
- Exactly the approved CSE/INFO seed sources are accepted unless more are intentionally added.
- Unregistered URLs are rejected by tests.

## Manual snapshot import

```bash
npm run ingest -- --source all
```

Expected outcome:

- New `snapshot_id` is created.
- Raw HTML snapshots are stored locally.
- CSE and INFO catalog courses are normalized into Course records.
- Allen School and UW Informatics pages are indexed as department context.
- Every indexed source has `retrieved_at` and `indexed_at` metadata.

## Run API

```bash
npm run dev:api
```

Expected outcome:

- API starts locally, for example at `http://localhost:3000`.
- `GET /workflows/nonexistent` returns a controlled 404 response.

## Search exact course code

```bash
curl -s -X POST http://localhost:3000/course-search \
  -H 'content-type: application/json' \
  -d '{"query":"CSE 142","mode":"exact_code"}'
```

Expected outcome:

- Response includes `workflow_id`.
- If course exists in indexed source, response includes a course result with title/description/credits when available.
- Substantive facts include citations.
- Freshness metadata includes snapshot/retrieval/index information when available.

## Search by department

```bash
curl -s -X POST http://localhost:3000/course-search \
  -H 'content-type: application/json' \
  -d '{"query":"CSE","mode":"department","filters":{"department":"CSE"}}'
```

Expected outcome:

- First page of ranked CSE results is returned.
- Results include citations/freshness and do not claim live availability.

## Natural-language discovery

```bash
curl -s -X POST http://localhost:3000/course-search \
  -H 'content-type: application/json' \
  -d '{"query":"intro programming courses","mode":"natural_language"}'
```

Expected outcome:

- Response returns ranked relevant courses from indexed CSE/INFO sources when available.
- Response includes limitations explaining snapshot-only/no-live-data behavior.
- No personalized advising or unsupported degree-planning claims are made.

## Course detail lookup

```bash
curl -s http://localhost:3000/courses/CSE-142
```

Expected outcome:

- Response includes normalized course fields when available.
- Each returned field includes citations or field provenance.
- Missing prerequisites/corequisites are marked unavailable rather than inferred.

## Workflow state inspection

```bash
curl -s http://localhost:3000/workflows/{workflow_id}
```

Expected outcome:

- Workflow state includes active query, interpreted filters, selected/retrieved courses, retrieved source IDs, citation IDs, freshness metadata, limitations, and status.

## Web UI validation

```bash
npm run dev:web
```

Expected outcome:

- Browser UI opens or is available locally.
- User can perform exact lookup, department search, keyword/NL search, and course-detail inspection.
- UI displays citations, freshness metadata, and limitation banners.
- UI preserves workflow ID across result selection.

## Test suite

```bash
npm test
npm run validate
```

Expected outcome:

- Source registry tests pass.
- Parser tests pass for saved CSE/INFO fixtures.
- Retrieval tests pass for exact, department, keyword, and natural-language cases.
- API contract tests pass against `contracts/openapi.yaml`.
- UI validation tests or manual checklist confirms required UI behavior.

## Release readiness checklist

- [ ] Approved source registry is present and validated.
- [ ] Manual ingestion completes from approved sources only.
- [ ] Exact course lookup meets validation target.
- [ ] Department/keyword/NL search meet validation target.
- [ ] Citations appear for substantive facts.
- [ ] Freshness metadata appears when available.
- [ ] Live-only requests are refused with clear limitation messaging.
- [ ] Workflow state persists across multi-step interactions.
- [ ] API and Web UI both exercise the same indexed/snapshot data path.
