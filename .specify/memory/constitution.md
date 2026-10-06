<!--
Sync Impact Report
Version change: N/A → 1.0.0
Added principles:
- Source-Grounded Academic Accuracy
- Citation and Traceability by Default
- Structured Retrieval Before Open-Ended Web Search
- Freshness and Temporal Awareness
- Privacy and Student Data Protection
- Robustness Against Stale, Conflicting, or Missing Data
- Persistent and Explicit Workflow State
- Major Feature Testability and Validation
- Ethical Automation Boundaries
Removed principles: None
Follow-up TODOs: None
-->

# UW Course Research Agent Constitution

## Core Purpose

The UW Course Research Agent helps users query, search, compare, and understand University of Washington course-related information. This includes courses, prerequisites, departments, schedules, credits, descriptions, availability, and related academic planning context.

The first version is intentionally simple: it is a read-only research assistant focused on reliable retrieval, clear answers, persistent workflow state, and validation of major features.

## Principles

### I. Source-Grounded Academic Accuracy

Course-related answers MUST be grounded in authoritative or clearly identified sources. The agent MUST NOT invent course details, prerequisites, availability, instructors, credits, grading options, or requirement applicability.

Acceptable sources include official UW course catalog pages, UW time schedule information, UW department pages, official academic calendar pages, approved local datasets, and user-provided documents that are clearly labeled as user-provided.

If information is unavailable, ambiguous, stale, or unsupported by retrieved sources, the agent MUST say so clearly.

**Rationale:** Course information can affect academic planning decisions. Unsupported or invented information is unacceptable.

### II. Citation and Traceability by Default

Substantive course-related answers MUST include source references or explain why no source is available.

When possible, answers SHOULD include source title, URL or document identifier, retrieval timestamp or data snapshot version, and relevant evidence.

The system MUST make it possible to trace important claims back to retrieved sources.

**Rationale:** Users need to verify course information independently before relying on it.

### III. Structured Retrieval Before Open-Ended Web Search

The agent MUST prefer structured, purpose-built retrieval tools before using open-ended web search.

Structured retrieval includes local indexed UW course data, UW catalog datasets or parsers, UW time schedule datasets or parsers, approved APIs, curated source snapshots, internal search indexes built from known UW sources, and user-provided documents relevant to the query.

The agent MAY use open-ended web search only when structured sources do not contain the needed information, the user explicitly asks for broader web research, current information is required and unavailable in the structured index, or the agent needs to discover an authoritative UW source not already known.

When open-ended web search is used, the agent MUST clearly label it and prefer official UW domains over third-party sources.

**Rationale:** Structured tools are more reliable, auditable, reproducible, and testable than generic web search.

### IV. Freshness and Temporal Awareness

The agent MUST treat course information as time-sensitive.

The system MUST track or expose freshness metadata where feasible, including academic quarter or year, source publication date when available, last crawl or index time, and whether the information comes from historical, current, or future data.

The agent MUST NOT imply that a course is currently offered unless the relevant source confirms it for the applicable quarter or academic year.

**Rationale:** UW course offerings, instructors, schedules, and prerequisites can change frequently.

### V. Privacy and Student Data Protection

The system MUST minimize collection, storage, and exposure of user data.

The agent MUST NOT request, store, or infer sensitive student information unless strictly required for an explicitly supported feature and approved by project maintainers.

Sensitive information includes student ID numbers, UW NetID credentials, grades, private academic records, disability accommodations, immigration or visa status, financial aid details, and private advising notes.

The system MUST NOT scrape, access, or automate private UW systems without authorization.

**Rationale:** Course search and academic planning may intersect with sensitive educational information. Privacy must be protected from the start.

### VI. Robustness Against Stale, Conflicting, or Missing Data

The agent MUST handle stale, conflicting, missing, unofficial, or ambiguous data explicitly.

When sources conflict, the agent MUST surface the conflict rather than silently choosing one answer. The agent SHOULD prefer more authoritative and more recent sources according to a documented source priority order.

The agent MUST handle missing data gracefully and distinguish official information from inferred, user-provided, or unofficial information.

**Rationale:** UW course information may be distributed across multiple systems, and those systems may differ or become outdated.

### VII. Persistent and Explicit Workflow State

Important workflow information MUST live in explicit, inspectable, persistent state. It MUST NOT depend on hidden variables, hidden global variables, implicit memory, untracked prompt context, or undocumented side effects.

Important workflow information includes active user query, assumed quarter, department, campus, selected courses, applied filters, retrieved source identifiers, citation metadata, clarification answers, search history relevant to the current task, current workflow step, unresolved uncertainty, and task status.

If information affects retrieval, ranking, recommendations, citations, workflow behavior, or final answers, it MUST be represented in the workflow state.

State SHOULD be serializable, debuggable, and recoverable across tool calls or process restarts where feasible.

**Rationale:** Explicit state improves reproducibility, debugging, testing, and reliability for multi-step research workflows.

### VIII. Major Feature Testability and Validation

All major features MUST be testable and MUST have corresponding validation before they are considered complete or release-ready.

The project MUST maintain a test suite or validation suite that verifies major capabilities, including course lookup, natural-language course search, structured retrieval, citation generation, quarter-specific availability handling, prerequisite lookup, filtering, persistent workflow state, ambiguity handling, stale or conflicting data handling, privacy-sensitive input handling, and supported API or user-interface behavior.

Each major feature MUST have clearly defined expected behavior and a repeatable way to verify that behavior.

Validation MAY include automated unit tests, integration tests, end-to-end tests, retrieval evaluation benchmarks, golden-answer test cases, or manual validation checklists when automation is not practical.

The project MUST keep validation updated as features evolve. A major feature MUST NOT be considered complete if it cannot be validated.

**Rationale:** A maintained validation suite ensures the agent's major capabilities continue to work as data sources, retrieval logic, prompts, tools, and workflows change.

### IX. Ethical Automation Boundaries

The first version of the agent MUST be read-only: search, retrieve, summarize, compare, and explain.

The agent MUST NOT automate actions that affect enrollment, registration, payment, grades, student records, or restricted UW systems.

The agent MUST NOT bypass UW access controls, authentication requirements, rate limits, robots.txt, or terms of service.

**Rationale:** The safest initial system is a research assistant, not an autonomous enrollment or records-management actor.

## Governance

This constitution governs product decisions, architecture, data ingestion, retrieval behavior, answer generation, state management, testing, and release readiness for the UW Course Research Agent.

Feature specifications and implementation plans MUST state how they comply with applicable principles.

Pull requests that affect major behavior SHOULD be reviewed for source grounding, citation behavior, structured retrieval usage, freshness handling, privacy impact, persistent state behavior, testability, and failure-mode handling.

Amendments require a written proposal describing the change, rationale, impact assessment, maintainer review, and a semantic version bump.

Versioning policy:

- MAJOR: Removes or redefines a core safety, privacy, accuracy, state, or validation principle.
- MINOR: Adds a new principle or materially expands governance.
- PATCH: Clarifies wording without changing governance meaning.

**Version**: 1.0.0  
**Ratified**: 2026-10-06  
**Last Amended**: 2026-10-06
