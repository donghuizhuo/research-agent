# Web UI validation

The static UI is served by the existing FastAPI app (`courseagent serve`). Search
uses `POST /course-search`; selection uses `GET /courses/{course_id}`. The returned
workflow ID is reused for follow-up searches and included with detail requests.
Append `?debug` to the UI URL to reveal the development-only workflow ID.

## Repeatable regressions

```bash
python -m pytest -q
WEB_UI_BROWSER_TESTS=1 python -m pytest tests/test_web_ui.py -q
node --check courseagent/web/app.js
```

The opt-in browser tests require Chrome and `chrome-devtools-axi` on PATH. They
start a real FastAPI server with an isolated, fixture-seeded SQLite database,
make actual search/detail requests, and stop the server afterward. No live UW
fetches or model credentials are required. Network/HTTP failures and delayed
responses are injected in the browser only to exercise recovery and stale-response
handling. Fixtures are test data, not a claim about the current UW catalog.

The API tests cover exact lookup followed by a missing lookup in the same workflow
and consecutive discovery searches without accumulated courses. Browser tests
cover search-button alignment, real suggestions, keyboard submission and suggestion
selection, ranked results, department browsing, source access, missing fields,
empty results, loading, HTTP/network errors, detail retry, and late detail responses.
Layout checks use actual 1440/1100 desktop and 390/320 mobile CSS-pixel viewports.

## Source/data prerequisites and API limits

Normal manual verification needs an indexed database. Run `courseagent ingest`
and verify it reports nonzero indexed courses before claiming live-source success.
The separately landed catalog parser repair supports current bold code/title/credit
headings as well as standalone code text blocks. Verify nonzero ingestion counts
and approved source links against a fresh database for real-source integration.
The browser regression fixtures remain independent of that live-source proof; a
fixture-seeded API alone does not prove that normal ingestion works.

There is no dedicated autocomplete endpoint. Debounced suggestions use actual
search responses, with incomplete course codes matched against the API's returned
department list. They cover up to five returned matches, not the entire catalog;
department retrieval currently returns at most 25 courses. A fully specified code
uses exact lookup and is not subject to the department-prefix window.

The search route does not apply the schema's `mode` or `filters`. The UI omits a
mode selector, uses a bare department query for browsing, and narrows returned
matches locally when a department is selected. It does not promise exhaustive
filtered search. Result order follows the API.

The detail route currently returns empty `field_provenance` and omits citation
`claim_field` and course freshness. The UI exposes generic course sources in that
case, and uses source timestamps/snapshot IDs actually returned in citations.
It does not fabricate per-field attribution or missing prerequisites/corequisites.
Field grouping is used if a response provides it. Source URLs permit only HTTP(S).

## Manual checks with indexed data

- Search `CSE 142`: exact result auto-opens detail; description, credits, sources,
  and unavailable fields are visible. Follow with `CSE 999`: old results/detail clear.
- Search `intro programming courses`, select a result, then search again: API order
  is preserved and prior results do not accumulate.
- Leave text empty and choose CSE/INFO: browse returned courses. Try a topic with a
  selected department to narrow the returned matches.
- Type a code prefix or topic: actual suggestions appear when the API returns
  matching courses. ArrowDown/Up navigates; Enter selects; Escape dismisses.
- Press Enter in the query field; Tab through result cards and source buttons.
- Inspect the permanent indexed-source/no-live-data banner and any API limitations
  or conflicts. Never interpret a catalog offering statement as live availability.
- Check loading, disconnected network, API 500, detail 404/retry, and no-results.
- At 320/390 mobile and desktop widths, verify the Search button remains contained
  and the document has no horizontal overflow, including open course detail.
