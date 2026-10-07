"""Grounding verification, conflict detection, and sensitive-input redaction."""

from __future__ import annotations

import re
from typing import Any

from courseagent.agents.schemas import Citation, CourseAnswer, CourseSearchResult


def verify_grounding(state: dict[str, Any]) -> dict[str, Any]:
    """Ensure each substantive retrieved field has a citation.

    Courses without per-field citations are not silently dropped; their
    uncited fields become limitation messages rather than authoritative facts.
    """

    courses = state.get("retrieved_courses", [])
    citations = state.get("citations", [])
    limitations = list(state.get("limitations", []))

    cited_course_ids = set()
    for c in citations:
        if isinstance(c, Citation):
            cited_course_ids.add(c.course_id)
        elif isinstance(c, dict):
            cited_course_ids.add(c.get("course_id"))
    for course in courses:
        if isinstance(course, dict):
            course_id = course.get("course_id")
            cid = course_id
        else:
            course_id = getattr(course, "course_id", None)
            cid = course_id
        if cid and cid not in cited_course_ids:
            limitations.append(f"Course {course_id} has no per-field citations in the current snapshot.")
    return {"limitations": limitations}


def detect_conflicts(courses: list[Any], citations: list[Any]) -> list[dict[str, Any]]:
    """Compare cited values for the same course field across sources."""

    grouped: dict[tuple[str, str], set[str]] = {}
    for citation in citations:
        if isinstance(citation, Citation):
            course_id, field, value = citation.course_id, citation.claim_field, citation.evidence_text
        else:
            course_id, field, value = citation.get("course_id"), citation.get("claim_field"), citation.get("evidence_text")
        if not course_id or not field:
            continue
        grouped.setdefault((course_id, field), set()).add(value)

    conflicts: list[dict[str, Any]] = []
    for (course_id, field), values in grouped.items():
        if len(values) > 1:
            values_list = sorted(values)
            conflicts.append(
                {
                    "course_id": course_id,
                    "field": field,
                    "value_a": values_list[0],
                    "value_b": values_list[1],
                    "status": "open",
                }
            )
    return conflicts


_SENSITIVE_PATTERNS = [
    re.compile(r"\b\d{7}\b"),  # UW student numbers
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # emails
    re.compile(r"\b(?:netid|net id|student id)\s*[:=]?\s*[A-Za-z0-9._-]+\b", re.IGNORECASE),
]


def redact_sensitive_input(query: str) -> str:
    """Strip student IDs and NetID-like tokens before state persistence/logging."""

    result = query
    for pattern in _SENSITIVE_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def has_quarter_confirmation(course: dict[str, Any] | None, quarter: str | None) -> bool:
    """Return True only if snapshot data confirms quarter-specific offering.

    For the MVP this is always False: live/quarter offering confirmation is
    out of scope, so no answer may claim it.
    """

    if not quarter or not course:
        return False
    return bool(course.get("quarters_offered") and quarter in course["quarters_offered"])
