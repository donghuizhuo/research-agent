# Catalog ingestion validation

`courseagent ingest uw_cse_catalog uw_info_catalog` uses the two existing approved
UW Seattle catalog URLs. Their course paragraphs contain a bold code, title and
parenthesized credit heading, followed by description text and a MyPlan link.
The parser extracts the heading and paragraph body separately, excludes the
MyPlan navigation text, and attributes every populated field to the source
document. Explicit Prerequisite/Corequisite clauses are retained verbatim;
absent fields remain unavailable. Headings without a code, title or credit group
are skipped. Standalone-code blocks remain supported.

Run `python -m pytest -q` for offline validation. The fixture-based ingestion test
replaces HTTP transport only: it exercises the approved registry, snapshot store,
normal CLI ingestion, parser, normalizer, SQLite/FTS indexing, API search and
course detail. It never seeds normalized courses. Fixtures are representative
paragraphs downloaded from the approved catalogs on 2026-10-07.

Live checks require network access, installed project dependencies and a writable
runtime data directory. Use a fresh runtime database to distinguish ingestion
results from previously indexed records. Course counts can change with UW's
catalog; the observed 161 CSE and 57 INFO records are not a fixed acceptance rule.
Search retrieves at most 25 records per department/discovery query. Existing
index refresh and workflow session behavior are outside this parser change.
The original web UI renders course details and citations inline; a separate
selectable detail pane belongs to the concurrent UI revision.
