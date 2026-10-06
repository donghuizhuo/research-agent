# Data Model: MVP UW Course Search

## Entity: SourceRegistryEntry

Represents one approved source or source group from `config/sources.yml`.

Fields:

- `id` string, unique, required.
- `name` string, required.
- `tier` integer, required: `1`, `2`, or `3`.
- `type` enum, required: `course_catalog`, `department`, `approved_snapshot`, `user_document`.
- `authority` enum, required: `official`, `approved`, `user_provided`.
- `department` string, optional but required for department-scoped sources.
- `url` string, required for URL-backed sources.
- `allowed_url_patterns` string array, required.
- `extraction_policy` enum: `normalized_facts_allowed`, `supporting_context_by_default`.
- `promotion_rule` string, required for Tier 2 department sources.
- `freshness` object with required/optional metadata policy.

Validation rules:

- Every ingested URL must match one approved registry entry.
- Tier 1 course catalog entries may populate normalized facts.
- Tier 2 department entries are supporting context by default.
- No source outside the registry may be fetched or indexed by default.

## Entity: Snapshot

Represents one manual ingestion run or source capture.

Fields:

- `snapshot_id` string, primary key.
- `created_at` timestamp, required.
- `refresh_mode` enum: `manual`, `scheduled`.
- `source_ids` string array.
- `status` enum: `created`, `fetching`, `parsed`, `indexed`, `failed`.
- `error_summary` string, optional.

State transitions:

```text
created -> fetching -> parsed -> indexed
created -> fetching -> failed
created -> fetching -> parsed -> failed
```

## Entity: SourceDocument

Represents raw or parsed content from one approved source in a snapshot.

Fields:

- `source_document_id` string, primary key.
- `source_id` string, references SourceRegistryEntry.
- `snapshot_id` string, references Snapshot.
- `url` string.
- `title` string, optional.
- `content_type` string, e.g. `text/html`.
- `raw_content_ref` string, path/key in snapshot store.
- `content_hash` string.
- `retrieved_at` timestamp.
- `indexed_at` timestamp, optional until indexed.
- `parse_status` enum: `pending`, `parsed`, `failed`, `skipped`.

Validation rules:

- `url` must be approved by the source registry.
- `retrieved_at` is required before indexing.
- `indexed_at` is required before source appears in answer citations.

## Entity: Course

Normalized UW Seattle course record.

Fields:

- `course_id` string, primary key, format `{DEPARTMENT}-{NUMBER}`.
- `campus` enum, v1 value `seattle`.
- `department_code` string.
- `course_number` string.
- `title` string, optional if unavailable.
- `description` string, optional if unavailable.
- `credits` string, optional.
- `prerequisites` string, optional.
- `corequisites` string, optional.
- `source_field_provenance` object mapping field name to Citation IDs or SourceDocument IDs.
- `freshness_metadata` object.
- `created_at` timestamp.
- `updated_at` timestamp.

Validation rules:

- `course_id`, `campus`, `department_code`, and `course_number` are required.
- Course facts may be null/empty only if unavailable from approved sources.
- Tier 1 facts take priority over Tier 2 facts.
- Tier 2 facts cannot overwrite conflicting Tier 1 facts silently.

## Entity: SearchDocument

Chunk indexed for keyword and natural-language discovery.

Fields:

- `search_document_id` string, primary key.
- `source_document_id` string, references SourceDocument.
- `course_id` string, optional reference to Course.
- `department_code` string, optional.
- `document_type` enum: `course_record`, `department_context`.
- `title` string.
- `body` string.
- `tokens` generated/indexed text.
- `freshness_metadata` object.

Validation rules:

- Department context chunks can support search results but do not become normalized facts unless promotion rules pass.
- Search results must include source/citation references.

## Entity: Citation

Connects an answer claim or normalized fact to evidence.

Fields:

- `citation_id` string, primary key.
- `source_document_id` string, references SourceDocument.
- `course_id` string, optional.
- `claim_field` string, e.g. `title`, `credits`, `description`, `prerequisites`, `search_context`.
- `evidence_text` string.
- `url` string.
- `source_title` string, optional.
- `snapshot_id` string.
- `retrieved_at` timestamp.
- `indexed_at` timestamp.

Validation rules:

- Substantive course facts in API/UI answers must include at least one citation or explicitly state that no supporting source is available.
- Citations must refer to approved source documents.

## Entity: Conflict

Represents material disagreement between sources.

Fields:

- `conflict_id` string, primary key.
- `course_id` string.
- `field` string.
- `source_a_citation_id` string.
- `source_b_citation_id` string.
- `value_a` string.
- `value_b` string.
- `status` enum: `open`, `reviewed`, `resolved`.
- `created_at` timestamp.

Validation rules:

- Conflicts affecting an answer must be surfaced to the user.
- Tier 1 should not be silently overwritten by Tier 2.

## Entity: WorkflowState

Explicit persisted state for multi-step course research.

Fields:

- `workflow_id` string, primary key.
- `active_query` string.
- `interpreted_filters` object.
- `selected_courses` string array.
- `retrieved_source_ids` string array.
- `citation_ids` string array.
- `freshness_metadata` object.
- `unresolved_uncertainty` string array.
- `limitations` string array.
- `status` enum: `active`, `needs_clarification`, `complete`, `failed`.
- `created_at` timestamp.
- `updated_at` timestamp.

Validation rules:

- Every API search response must include or create a `workflow_id`.
- Workflow state must persist retrieved sources, citations, freshness metadata, limitations, and unresolved uncertainty.

## Entity Relationships

```text
SourceRegistryEntry 1 -> many SourceDocument
Snapshot 1 -> many SourceDocument
SourceDocument 1 -> many SearchDocument
SourceDocument 1 -> many Citation
Course 1 -> many Citation
Course 1 -> many SearchDocument
Course 1 -> many Conflict
WorkflowState many -> many Course via selected_courses
WorkflowState many -> many Citation via citation_ids
```
