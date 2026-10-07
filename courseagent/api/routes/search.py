"""POST /course-search route."""

from __future__ import annotations

from fastapi import APIRouter, Request

from courseagent.api.schemas import (
    CitationModel,
    CourseResult,
    CourseSearchRequest,
    CourseSearchResponse,
    FreshnessMetadataModel,
)

router = APIRouter()


def _citation_from_graph(citation: dict) -> CitationModel:
    return CitationModel(
        citation_id=citation.get("citation_id", ""),
        source_id=citation.get("source_document_id") or citation.get("source_id"),
        source_title=citation.get("source_title"),
        url=citation.get("url", ""),
        evidence_text=citation.get("evidence_text", ""),
        claim_field=citation.get("claim_field"),
        snapshot_id=citation.get("snapshot_id"),
        retrieved_at=citation.get("retrieved_at"),
        indexed_at=citation.get("indexed_at"),
    )


def _freshness_from_graph(freshness: list[dict] | None) -> FreshnessMetadataModel | None:
    if not freshness:
        return None
    first = freshness[0]
    return FreshnessMetadataModel(
        snapshot_id=first.get("snapshot_id"),
        retrieved_at=first.get("retrieved_at"),
        indexed_at=first.get("indexed_at"),
    )


@router.post("/course-search", response_model=CourseSearchResponse)
def search_courses(payload: CourseSearchRequest, request: Request) -> CourseSearchResponse:
    from courseagent.api.app import get_graph

    graph = get_graph(request.app)
    result = graph.run(payload.query, workflow_id=payload.workflow_id)

    structured = result.get("structured_answer") or {}
    results: list[CourseResult] = []
    course_list = structured.get("ranked_courses") or ([structured["course"]] if structured.get("course") else [])
    for course in course_list:
        if not course:
            continue
        citations = [_citation_from_graph(c) for c in course.get("citations", [])]
        results.append(
            CourseResult(
                course_id=course.get("course_id", ""),
                title=course.get("title"),
                department=course.get("department_code", ""),
                course_number=course.get("course_number", ""),
                credits=course.get("credits"),
                summary=course.get("description"),
                citations=citations,
                freshness=_freshness_from_graph(course.get("freshness")),
            )
        )

    if result.get("needs_clarification"):
        answer_type = "clarification_needed"
    elif not results:
        answer_type = "no_results"
    elif len(results) == 1 and not structured.get("ranked_courses"):
        answer_type = "direct_answer"
    else:
        answer_type = "ranked_courses"

    return CourseSearchResponse(
        workflow_id=result["workflow_id"],
        answer_type=answer_type,
        results=results,
        limitations=result.get("limitations", []),
        conflicts=[],
        state_ref=f"/workflows/{result['workflow_id']}",
    )


def register(app) -> None:
    app.include_router(router)
