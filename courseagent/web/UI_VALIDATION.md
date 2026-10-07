# Web UI Validation Checklist

Maps UI behaviors to `contracts/ui-contract.md` scenarios. Mark each item after
manually verifying against a seeded database (`courseagent ingest` or a fixture).

## Exact course-code lookup

- [ ] Search `CSE 142` shows a single course card with title, credits, and description.
- [ ] Course card shows at least one citation with evidence text and source URL.
- [ ] Course card shows freshness metadata (retrieved_at and snapshot_id).

## Department / keyword / natural-language search

- [ ] Search `INFO` or `INFO courses` shows ranked course cards.
- [ ] Search a keyword (e.g. `programming`) shows matching courses.
- [ ] Search natural language (e.g. `introductory programming course`) shows matches.

## Limitations

- [ ] Search for a missing course (e.g. `CSE 999`) shows a "no matching courses" message.
- [ ] Search for out-of-scope content (e.g. `enrollment in CSE 142`) shows a limitation banner.
- [ ] Live-only requests (seats, registration status) are labeled as out of scope, never answered authoritatively.

## Citations and freshness

- [ ] Every substantive field (title, credits, description) has a citation.
- [ ] Uncited fields are downgraded to limitation messages rather than asserted.

## Error handling

- [ ] Invalid/empty query does not crash the UI.
- [ ] API/network errors render an error message in the results area.
