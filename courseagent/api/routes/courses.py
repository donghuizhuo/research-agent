"""GET /courses/{course_id} route."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from courseagent.api.routes.search import _citation_from_graph
from courseagent.api.schemas import CitationModel, CourseDetailResponse

router = APIRouter()


@router.get("/courses/{course_id}", response_model=CourseDetailResponse)
def get_course(course_id: str, request: Request) -> CourseDetailResponse:
    from courseagent.api.app import get_graph
    from courseagent.dataflows import retrieval

    graph = get_graph(request.app)
    conn = graph._ensure_conn()
    row = retrieval.find_course_by_code(conn, course_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found in approved indexed sources.")

    citation_rows = retrieval.fetch_citations(conn, course_id.upper())
    citations = [
        CitationModel(
            citation_id=c["citation_id"],
            source_id=c["source_document_id"],
            source_title=c["source_title"],
            url=c["url"],
            evidence_text=c["evidence_text"],
            snapshot_id=c["snapshot_id"],
            retrieved_at=c["retrieved_at"],
            indexed_at=c["indexed_at"],
        )
        for c in citation_rows
    ]

    return CourseDetailResponse(
        course_id=row["course_id"],
        title=row["title"],
        department=row["department_code"],
        course_number=row["course_number"],
        credits=row["credits"],
        summary=row["description"],
        description=row["description"],
        prerequisites=row["prerequisites"],
        corequisites=row["corequisites"],
        citations=citations,
        field_provenance={},
    )


def register(app) -> None:
    app.include_router(router)
