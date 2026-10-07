"""FastAPI request/response models matching contracts/openapi.yaml."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    auto = "auto"
    exact_code = "exact_code"
    department = "department"
    keyword = "keyword"
    natural_language = "natural_language"


class CourseFilters(BaseModel):
    campus: Literal["seattle"] | None = "seattle"
    department: str | None = None
    level: str | None = None
    quarter: str | None = None


class CourseSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    mode: SearchMode = SearchMode.auto
    filters: CourseFilters = Field(default_factory=CourseFilters)
    workflow_id: str | None = None


class CitationModel(BaseModel):
    citation_id: str
    source_id: str | None = None
    source_title: str | None = None
    url: str
    evidence_text: str
    claim_field: str | None = None
    snapshot_id: str | None = None
    retrieved_at: str | None = None
    indexed_at: str | None = None


class FreshnessMetadataModel(BaseModel):
    snapshot_id: str | None = None
    source_date: str | None = None
    retrieved_at: str | None = None
    indexed_at: str | None = None


class CourseResult(BaseModel):
    course_id: str
    title: str | None = None
    department: str
    course_number: str
    credits: str | None = None
    summary: str | None = None
    citations: list[CitationModel] = Field(default_factory=list)
    freshness: FreshnessMetadataModel | None = None
    score: float | None = None


class ConflictSummary(BaseModel):
    conflict_id: str | None = None
    course_id: str
    field: str
    message: str | None = None
    citation_ids: list[str] = Field(default_factory=list)


class CourseSearchResponse(BaseModel):
    workflow_id: str
    answer_type: Literal["ranked_courses", "direct_answer", "clarification_needed", "no_results"]
    results: list[CourseResult] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    conflicts: list[ConflictSummary] = Field(default_factory=list)
    state_ref: str | None = None


class CourseDetailResponse(CourseResult):
    description: str | None = None
    prerequisites: str | None = None
    corequisites: str | None = None
    field_provenance: dict[str, list[CitationModel]] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class WorkflowStateModel(BaseModel):
    workflow_id: str
    active_query: str
    interpreted_filters: dict = Field(default_factory=dict)
    selected_courses: list[str] = Field(default_factory=list)
    retrieved_source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    freshness_metadata: dict = Field(default_factory=dict)
    unresolved_uncertainty: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    status: Literal["active", "needs_clarification", "complete", "failed"]
    updated_at: str | None = None


class SnapshotImportResponse(BaseModel):
    snapshot_id: str | None = None
    status: Literal["accepted", "completed", "failed"]
    imported_source_ids: list[str] = Field(default_factory=list)
    message: str | None = None


class ErrorResponse(BaseModel):
    error: str
    message: str | None = None
    limitations: list[str] = Field(default_factory=list)
