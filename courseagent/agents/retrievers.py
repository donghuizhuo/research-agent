"""Deterministic retrieval nodes for the course research graph."""

from __future__ import annotations

from typing import Any

from courseagent.agents.schemas import (
    Citation,
    CourseSearchResult,
    FreshnessMetadata,
    QueryIntent,
)
from courseagent.dataflows import retrieval as r


def _citation_from_row(row: dict[str, Any]) -> Citation:
    return Citation(
        citation_id=row.get("citation_id", ""),
        source_document_id=row.get("source_document_id"),
        course_id=row.get("course_id"),
        claim_field=row.get("claim_field"),
        evidence_text=row.get("evidence_text", ""),
        url=row.get("url", ""),
        source_title=row.get("source_title"),
        snapshot_id=row.get("snapshot_id"),
        retrieved_at=row.get("retrieved_at"),
        indexed_at=row.get("indexed_at"),
    )


def _result_from_row(row: dict[str, Any], citations: list[Citation]) -> CourseSearchResult:
    return CourseSearchResult(
        course_id=row.get("course_id", ""),
        campus=row.get("campus", "seattle"),
        department_code=row.get("department_code", ""),
        course_number=row.get("course_number", ""),
        title=row.get("title"),
        description=row.get("description"),
        credits=row.get("credits"),
        prerequisites=row.get("prerequisites"),
        corequisites=row.get("corequisites"),
        citations=citations,
    )


def _result_for_row_with_citations(row: dict[str, Any], conn: Any) -> tuple[CourseSearchResult, list[Citation]]:
    course_id = row.get("course_id")
    if not course_id:
        return _result_from_row(row, []), []
    citation_rows = r.fetch_citations(conn, course_id)
    citations = [_citation_from_row(c) for c in citation_rows]
    return _result_from_row(row, citations), citations


def _freshness_from_rows(rows: list[dict[str, Any]]) -> list[FreshnessMetadata]:
    seen: set[str] = set()
    out: list[FreshnessMetadata] = []
    for row in rows:
        snapshot_id = row.get("snapshot_id")
        if not snapshot_id or snapshot_id in seen:
            continue
        seen.add(snapshot_id)
        out.append(
            FreshnessMetadata(
                snapshot_id=snapshot_id,
                source_id=row.get("source_document_id") or row.get("source_id"),
                retrieved_at=row.get("retrieved_at"),
                indexed_at=row.get("indexed_at"),
            )
        )
    return out


def _run_retrieval(state: dict[str, Any], conn: Any, course_id: str) -> dict[str, Any]:
    row = r.find_course_by_code(conn, course_id)
    if row is None:
        return {
            "retrieved_courses": [],
            "citations": [],
            "freshness": [],
            "limitations": [f"No indexed course found for {course_id}. It may be out of v1 scope or not yet ingested."],
            "status": "not_found",
        }
    citation_rows = r.fetch_citations(conn, course_id)
    citations = [_citation_from_row(c) for c in citation_rows]
    result = _result_from_row(row, citations)
    return {
        "retrieved_courses": [result],
        "citations": citations,
        "freshness": _freshness_from_rows(citation_rows) if citation_rows else _freshness_from_rows([row]),
        "status": "ok",
    }


def exact_code_retriever(state: dict[str, Any]) -> dict[str, Any]:
    conn = state.get("conn")
    intent = state.get("intent")
    course_id = None
    if isinstance(intent, QueryIntent):
        course_id = intent.course_id
    if not course_id:
        course_id = state.get("query", "").strip().upper().replace(" ", "-")
    return _run_retrieval(state, conn, course_id)


def department_retriever(state: dict[str, Any]) -> dict[str, Any]:
    conn = state.get("conn")
    intent = state.get("intent")
    dept = intent.department_code if isinstance(intent, QueryIntent) else None
    if not dept:
        dept = state.get("query", "").strip().upper()
    rows = r.search_department(conn, dept)
    results: list[CourseSearchResult] = []
    all_citations: list[Citation] = []
    for row in rows:
        result, citations = _result_for_row_with_citations(row, conn)
        results.append(result)
        all_citations.extend(citations)
    if not results:
        return {"retrieved_courses": [], "citations": [], "freshness": [], "limitations": [f"No courses found for department {dept}."], "status": "not_found"}
    return {"retrieved_courses": results, "citations": all_citations, "status": "ok"}


def keyword_retriever(state: dict[str, Any]) -> dict[str, Any]:
    conn = state.get("conn")
    intent = state.get("intent")
    keyword = intent.keyword if isinstance(intent, QueryIntent) else None
    if not keyword:
        keyword = state.get("query", "").strip()
    rows = r.search_keyword(conn, keyword)
    results: list[CourseSearchResult] = []
    all_citations: list[Citation] = []
    for row in rows:
        if not row.get("course_id"):
            continue
        result, citations = _result_for_row_with_citations(row, conn)
        results.append(result)
        all_citations.extend(citations)
    if not results:
        return {"retrieved_courses": [], "citations": [], "freshness": [], "limitations": [f"No keyword matches for '{keyword}'."], "status": "not_found"}
    return {"retrieved_courses": results, "citations": all_citations, "status": "ok"}


def natural_language_retriever(state: dict[str, Any]) -> dict[str, Any]:
    conn = state.get("conn")
    query = state.get("query", "")
    rows = r.search_natural_language(conn, query)
    results: list[CourseSearchResult] = []
    all_citations: list[Citation] = []
    for row in rows:
        if not row.get("course_id"):
            continue
        result, citations = _result_for_row_with_citations(row, conn)
        results.append(result)
        all_citations.extend(citations)
    if not results:
        return {"retrieved_courses": [], "citations": [], "freshness": [], "limitations": [f"No natural-language matches for '{query}'."], "status": "not_found"}
    return {"retrieved_courses": results, "citations": all_citations, "status": "ok"}
