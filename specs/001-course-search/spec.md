# Feature Specification: MVP UW Course Search

**Feature Branch**: `001-course-search`  
**Created**: 2026-10-06  
**Status**: Draft  
**Input**: User request: "Create the first MVP feature spec for course search."

## Clarifications

### Session 2026-10-06

- Q: Which UW Seattle source coverage should v1 require? → A: Official UW catalog/course descriptions and official UW department pages; no UW Time Schedule requirement for v1.
- Q: Should natural-language course search be required for the v1 MVP, or treated as a stretch feature? → A: Required in v1, limited to indexed/snapshot course-source search.
- Q: What should the v1 user-facing surface be? → A: Both a direct API and a simple Web UI.
- Q: What snapshot refresh cadence should v1 assume? → A: Manual refresh for MVP; scheduled refresh later.
- Q: How strict should department-page extraction be before treating content as a normalized course fact? → A: Strict: catalog/course descriptions own normalized facts; department pages are supporting context unless clearly structured.
- Q: How should approved v1 sources be controlled? → A: Use an explicit source registry with source tiers, URL allowlists, extraction policies, and freshness requirements.
- Q: Which initial source seed should v1 use? → A: CSE and INFO catalog pages plus Allen School and UW Informatics department pages.

## User Scenarios & Testing

### Primary User Story

As a UW Seattle course researcher, I want to search for UW Seattle courses using course codes, departments, keywords, or natural-language questions so that I can quickly find grounded course information with citations and understand whether the information is current, missing, stale, or conflicting.

### Acceptance Scenarios

1. **Given** a user asks for a specific course by course code, **When** the course exists in the available structured UW Seattle course data, **Then** the system returns the course title, department, course number, credits when available, description when available, and citations for the returned facts.

2. **Given** a user searches by department or keyword, **When** matching courses exist, **Then** the system returns a concise ranked list of relevant courses with enough information for the user to choose which course to inspect further.

3. **Given** a user asks a natural-language course discovery question, **When** the question can be answered from approved indexed or snapshot UW Seattle course sources, **Then** the system interprets the request, retrieves and ranks relevant courses or facts, and returns an answer grounded in cited sources without providing personalized advising or unsupported requirement inferences.

4. **Given** a user asks about prerequisites, **When** prerequisite information is available in the retrieved sources, **Then** the system returns the prerequisite information with citations and does not infer missing prerequisites.

5. **Given** a user asks whether a course is offered in a particular quarter, **When** quarter-specific availability data is available in approved indexed or snapshot sources, **Then** the system answers for that quarter with freshness metadata and citations and identifies that the answer is not a live registration-status check.

6. **Given** a user asks whether a course is offered in a particular quarter, **When** quarter-specific availability data is not available in approved indexed or snapshot sources, **Then** the system clearly states that availability cannot be confirmed from available sources and does not query or imply access to live UW registration systems.

7. **Given** structured retrieval does not contain the requested information, **When** open-ended web search is not explicitly requested or otherwise justified, **Then** the system does not present generic web search results as authoritative course facts.

8. **Given** sources conflict, **When** the conflict affects the answer, **Then** the system surfaces the conflict and identifies the sources involved rather than silently choosing one answer.

9. **Given** a user provides sensitive student information, **When** that information is not needed for course search, **Then** the system avoids storing or using it and responds without requiring private student data.

### Edge Cases

- User enters an invalid or nonexistent course code.
- User enters an ambiguous course code or department abbreviation.
- User asks about a course title that matches multiple departments.
- User asks for courses using informal terms, such as "easy stats class" or "machine learning intro."
- User asks for current enrollment, seats, live registration status, instructor, or time schedule details when those fields are unavailable or only available from live systems.
- User asks a natural-language question that requires personalized degree-planning advice, official advising verification, or unsupported inference beyond indexed/snapshot course sources.
- User asks for information outside the available UW Seattle course data or outside the Seattle campus scope.
- User asks a follow-up question that depends on prior filters or selected courses.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST limit MVP course search scope to UW Seattle campus courses.
- **FR-002**: The system MUST allow users to search for UW Seattle courses by exact course code.
- **FR-003**: The system MUST allow users to search for UW Seattle courses by department.
- **FR-004**: The system MUST allow users to search for UW Seattle courses by keyword appearing in available course titles, descriptions, or related indexed course text.
- **FR-005**: The system MUST support natural-language course search for common course discovery questions within the UW Seattle scope, limited to retrieval and ranking over approved indexed or snapshot course sources.
- **FR-006**: The system MUST return course title, department, course number, and description when those fields are available from retrieved sources.
- **FR-007**: The system MUST return credit information when available from retrieved sources.
- **FR-008**: The system MUST return prerequisite or corequisite information only when supported by retrieved sources.
- **FR-008a**: The system MUST NOT provide personalized advising, degree-planning recommendations, or requirement applicability claims from natural-language search unless those claims are directly supported by retrieved sources.
- **FR-009**: The system MUST include citations or source references for substantive course facts.
- **FR-010**: The system MUST state when a requested course fact is unavailable from the available sources.
- **FR-011**: The system MUST prefer structured UW course retrieval sources before using open-ended web search.
- **FR-011a**: The system MUST include official UW catalog/course description sources and official UW department pages in v1 source coverage.
- **FR-012**: The system MUST clearly label any answer that uses open-ended web search.
- **FR-013**: The system MUST track and expose freshness metadata when available, including academic quarter, academic year, source date, or retrieval/index timestamp.
- **FR-014**: The system MUST NOT claim that a course is offered in a specific quarter unless approved indexed or snapshot sources confirm that offering for that quarter.
- **FR-015**: The system MUST NOT depend on live UW systems or real-time course availability for MVP answers.
- **FR-016**: The system MUST clearly communicate that real-time enrollment, seat availability, live registration status, and live schedule changes are out of scope for v1.
- **FR-017**: The system MUST surface material conflicts between retrieved sources when those conflicts affect the answer.
- **FR-018**: The system MUST distinguish official UW information from user-provided, inferred, or unofficial information.
- **FR-019**: The system MUST maintain explicit workflow state for active query, applied filters, selected course or course set, retrieved source identifiers, citation metadata, freshness metadata, unresolved uncertainty, and current task status.
- **FR-020**: The system MUST NOT depend on hidden variables, hidden global variables, or untracked implicit memory for retrieval, filtering, citation, or answer behavior.
- **FR-021**: The system MUST avoid requesting, storing, or using sensitive student information for MVP course search.
- **FR-022**: The system MUST be read-only and MUST NOT perform enrollment, registration, payment, grade, or private student-record actions.
- **FR-023**: The system MUST provide user-facing messages for invalid, ambiguous, missing, stale, conflicting, out-of-scope campus, or live-only data cases.
- **FR-024**: The system MUST support validation of major course search capabilities through repeatable tests or documented validation procedures.
- **FR-025**: The system MUST expose v1 course search through both a direct API and a simple Web UI.
- **FR-026**: The system MUST support manual snapshot refresh for MVP and MUST preserve design compatibility with scheduled refresh after v1.
- **FR-027**: The system MUST treat official UW catalog/course descriptions as the primary source for normalized course facts in v1; department pages MAY provide supporting searchable context or normalized facts only when the fact is clearly structured and directly cited.
- **FR-028**: The system MUST control v1 ingestion through an explicit source registry that records source tier, type, authority, approved URL patterns or URLs, extraction policy, and freshness requirements.

### Key Entities

- **Course**: A UW Seattle course identified by department and number. Includes title, description, credits, prerequisites, and related metadata when available.
- **Course Source**: A source of course facts, such as an official UW catalog record, official UW course description, official UW department page, approved snapshot or local dataset, or user-provided document.
- **Citation**: A reference connecting an answer claim to a Course Source. Includes source identifier and, when available, URL, title, retrieval timestamp, and relevant evidence.
- **Freshness Metadata**: Information describing the time validity of a source or answer, such as quarter, academic year, publication date, index timestamp, or retrieval timestamp.
- **Search Query**: The user's current course-search request, including exact text and interpreted filters.
- **Workflow State**: Inspectable persisted state for the active research workflow, including query, assumptions, filters, selected courses, retrieved sources, citations, unresolved uncertainty, and status.

## Success Criteria

- **SC-001**: At least 95% of exact UW Seattle course-code searches in the validation set return the correct course when the course exists in available structured data.
- **SC-002**: At least 90% of keyword, department, or natural-language course discovery searches in the validation set return at least one relevant course in the first five results when relevant courses exist.
- **SC-003**: 100% of validation answers containing substantive course facts include at least one citation or explicitly state that no supporting source is available.
- **SC-004**: 100% of validation cases for unavailable quarter-specific offering data avoid claiming confirmed availability or live registration status.
- **SC-005**: 100% of validation cases involving missing or conflicting required facts clearly communicate the limitation or conflict to the user.
- **SC-006**: 100% of validation workflows preserve required workflow state fields across multi-step course search interactions.
- **SC-007**: 100% of major MVP course-search capabilities have repeatable tests, evaluation cases, or documented validation procedures.
- **SC-008**: Users in validation can complete a basic course lookup task in no more than two interactions when the course code is known and the course exists in available data.
- **SC-009**: Both the API and Web UI can complete exact course lookup, keyword/department search, natural-language search, and course-detail retrieval using the same indexed/snapshot data and citation requirements.

## Assumptions

- The MVP is limited to UW Seattle campus courses and publicly available or approved UW course-related information.
- Courses from other UW campuses are out of scope for the MVP unless they appear in approved UW Seattle course sources and are clearly relevant to Seattle course search.
- The MVP is read-only and does not interact with private UW registration, advising, grade, payment, or student-record systems.
- Initial v1 source seed includes UW CSE Catalog, Allen School, UW INFO Catalog, and UW Informatics sources as listed in `config/sources.yml`.
- Required v1 source coverage includes official UW catalog/course description sources and explicitly allowlisted official UW department pages for UW Seattle courses.
- Official UW catalog/course descriptions are the primary source for normalized course facts; department pages are supporting context unless facts are clearly structured and directly cited.
- UW Time Schedule data is not required source coverage for v1 unless provided through approved indexed or snapshot data.
- Structured retrieval sources are available or will be created before release.
- The MVP uses approved indexed or snapshot UW Seattle course data and does not depend on live UW systems.
- MVP snapshot refresh is manual; scheduled refresh is deferred until after v1.
- Quarter-specific availability is supported only when relevant approved indexed or snapshot availability data is available.
- Real-time enrollment, seat availability, live registration status, and live schedule changes are out of scope for v1.
- Open-ended web search is a fallback, not the default retrieval path.
- The first release may support a limited set of UW Seattle course data sources as long as the system clearly communicates source coverage and limitations.

## Constitution Alignment

- **Source-Grounded Academic Accuracy**: Requirements mandate cited, source-grounded course facts and explicit handling of unavailable data.
- **Citation and Traceability by Default**: Requirements and success criteria require citations for substantive claims.
- **Structured Retrieval Before Open-Ended Web Search**: Requirements establish structured retrieval as the default and web search as labeled fallback.
- **Freshness and Temporal Awareness**: Requirements and success criteria require freshness metadata and prevent unsupported offering claims.
- **Privacy and Student Data Protection**: Requirements exclude unnecessary sensitive student information.
- **Robustness Against Stale, Conflicting, or Missing Data**: Requirements include explicit handling for missing, stale, ambiguous, and conflicting information.
- **Persistent and Explicit Workflow State**: Requirements define inspectable state and prohibit hidden state dependencies.
- **Major Feature Testability and Validation**: Requirements and success criteria require repeatable validation for major MVP capabilities.
- **Ethical Automation Boundaries**: Requirements keep the MVP read-only and prohibit restricted UW actions.
