"""LangGraph state definition for the course research workflow."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph import MessagesState

from courseagent.agents.schemas import Citation, CourseAnswer, CourseSearchResult, FreshnessMetadata, QueryIntent


def merge_lists(left: list[Any] | None, right: list[Any] | None) -> list[Any]:
    """Append list state updates while tolerating None values."""

    return [*(left or []), *(right or [])]


def replace_dict(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Shallow-merge dictionary state updates."""

    return {**(left or {}), **(right or {})}


class CourseResearchState(MessagesState):
    """Persistent graph state for a single course-research workflow."""

    query: str
    intent: QueryIntent | str | None
    interpreted_filters: Annotated[dict[str, Any], replace_dict]
    retrieved_courses: Annotated[list[CourseSearchResult | dict[str, Any]], merge_lists]
    citations: Annotated[list[Citation | dict[str, Any]], merge_lists]
    freshness: Annotated[list[FreshnessMetadata | dict[str, Any]], merge_lists]
    answer: str | None
    structured_answer: CourseAnswer | dict[str, Any] | None
    limitations: Annotated[list[str], merge_lists]
    conflicts: Annotated[list[dict[str, Any]], merge_lists]
    needs_clarification: bool
    status: str


class CourseResearchStateInput(TypedDict, total=False):
    query: str
    workflow_id: str
