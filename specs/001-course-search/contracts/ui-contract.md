# UI Contract: MVP UW Course Search Web UI

## Purpose

The Web UI exposes the same course-search capabilities as the API while making source grounding, freshness, limitations, and workflow state visible to users.

## Pages / Views

### Search View

Required elements:

- Search input accepting exact course codes, departments, keywords, and natural-language discovery queries.
- Optional department filter for CSE/INFO in first seed.
- Submit action.
- Snapshot/no-live-data limitation banner.
- Current `workflow_id` display or debug affordance in development builds.

Expected behavior:

- On submit, call `POST /course-search`.
- Preserve returned `workflow_id` for follow-up searches.
- Show invalid/out-of-scope messages from API without inventing results.

### Results View

Required elements per result:

- Course ID.
- Title when available.
- Department and course number.
- Credits when available.
- Short summary or matched evidence.
- Citation count or citation links.
- Freshness summary.

Expected behavior:

- Results are ranked in API order.
- Selecting a result calls `GET /courses/{course_id}?workflow_id=...`.
- If no results, show API limitations and suggested next action.

### Course Detail View

Required elements:

- Course title, department, number.
- Description.
- Credits.
- Prerequisites/corequisites when available.
- Citations grouped by field when available.
- Freshness metadata.
- Conflicts and limitations if present.

Expected behavior:

- Do not hide missing fields; show “Unavailable from indexed sources” or equivalent.
- Do not show quarter-specific offering as confirmed unless API says so with citation.

### Citation Panel

Required elements:

- Source title/name.
- URL or document identifier.
- Evidence text/snippet.
- Snapshot ID when available.
- Retrieved/indexed timestamps when available.

Expected behavior:

- Citation panel must be reachable from any substantive fact shown in detail view.

### Limitation Banner

Always communicate for MVP:

- Data is from approved indexed/snapshot sources.
- No live enrollment, seat availability, live registration status, or live schedule changes.

Show contextual limitations for:

- Missing facts.
- Ambiguous query.
- Out-of-scope campus.
- Live-only request.
- Conflicting sources.

## Accessibility / UX Constraints

- Use semantic headings and buttons.
- Results and citations must be keyboard reachable.
- Limitation and error messages must be visible text, not color-only indicators.
- Citation URLs should open in a new browser tab/window.

## Validation Scenarios

1. Exact lookup displays a CSE course with citation and freshness metadata.
2. Department search for CSE returns ranked results.
3. Natural-language query such as “intro programming courses” returns relevant CSE/INFO courses when present in indexed sources.
4. Live-only query such as “how many seats are open?” shows no-live-data limitation.
5. Course detail view displays unavailable prerequisites as unavailable rather than inferred.
6. Workflow ID persists across search and course-detail interactions.
