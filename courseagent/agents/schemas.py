"""Shared Pydantic schemas and rendering helpers for grounded course answers."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryIntentType(str, Enum):
    exact_code = "exact_code"
    department = "department"
    keyword = "keyword"
    natural_language = "natural_language"
    ambiguous = "ambiguous"
    out_of_scope = "out_of_scope"


class QueryIntent(BaseModel):
    """Structured interpretation of a user query."""

    intent: QueryIntentType
    department_code: str | None = None
    course_number: str | None = None
    course_id: str | None = None
    keyword: str | None = None
    natural_language_query: str | None = None
    campus: str | None = "seattle"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str | None = None


class FreshnessMetadata(BaseModel):
    snapshot_id: str | None = None
    source_id: str | None = None
    retrieved_at: str | None = None
    indexed_at: str | None = None
    refresh_mode: Literal["manual", "scheduled"] | None = "manual"
    source_date: str | None = None


class Citation(BaseModel):
    citation_id: str
    source_document_id: str | None = None
    course_id: str | None = None
    claim_field: str | None = None
    evidence_text: str
    url: str
    source_title: str | None = None
    snapshot_id: str | None = None
    retrieved_at: str | None = None
    indexed_at: str | None = None


class CourseSearchResult(BaseModel):
    course_id: str
    campus: str = "seattle"
    department_code: str
    course_number: str
    title: str | None = None
    description: str | None = None
    credits: str | None = None
    prerequisites: str | None = None
    corequisites: str | None = None
    score: float | None = None
    citations: list[Citation] = Field(default_factory=list)
    freshness: list[FreshnessMetadata] = Field(default_factory=list)


class CourseAnswer(BaseModel):
    query: str
    answer: str
    intent: QueryIntentType | None = None
    course: CourseSearchResult | None = None
    ranked_courses: list[CourseSearchResult] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    freshness: list[FreshnessMetadata] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    workflow_id: str | None = None
    status: str = "ok"


def render_citation(citation: Citation) -> str:
    title = citation.source_title or citation.url
    parts = [f"{title}: {citation.evidence_text}", f"URL: {citation.url}"]
    if citation.retrieved_at:
        parts.append(f"retrieved_at={citation.retrieved_at}")
    if citation.snapshot_id:
        parts.append(f"snapshot={citation.snapshot_id}")
    return " | ".join(parts)


def render_course_result(course: CourseSearchResult) -> str:
    heading = f"{course.department_code} {course.course_number}"
    if course.title:
        heading += f" — {course.title}"
    fields = [heading]
    if course.credits:
        fields.append(f"Credits: {course.credits}")
    if course.description:
        fields.append(course.description)
    if course.prerequisites:
        fields.append(f"Prerequisites: {course.prerequisites}")
    if course.corequisites:
        fields.append(f"Corequisites: {course.corequisites}")
    return "\n".join(fields)


def render_answer(answer: CourseAnswer) -> str:
    sections = [answer.answer]
    if answer.ranked_courses:
        sections.append("\nResults:\n" + "\n\n".join(render_course_result(c) for c in answer.ranked_courses))
    elif answer.course:
        sections.append("\n" + render_course_result(answer.course))
    if answer.limitations:
        sections.append("\nLimitations:\n" + "\n".join(f"- {item}" for item in answer.limitations))
    if answer.citations:
        sections.append("\nSources:\n" + "\n".join(f"- {render_citation(c)}" for c in answer.citations))
    return "\n".join(sections)
