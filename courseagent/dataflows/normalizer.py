"""Course normalization enforcing course_id format and campus scope."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from courseagent.dataflows.parsers.uw_course_catalog import ParsedCourse

CAMPUS = "seattle"


@dataclass
class NormalizedCourse:
    course_id: str
    campus: str
    department_code: str
    course_number: str
    title: str | None = None
    description: str | None = None
    credits: str | None = None
    prerequisites: str | None = None
    corequisites: str | None = None
    source_field_provenance: dict[str, str] = field(default_factory=dict)
    freshness_metadata: dict[str, Any] = field(default_factory=dict)


def normalize_course(parsed: ParsedCourse, snapshot_id: str, source_id: str) -> NormalizedCourse:
    """Normalize a single parsed course record."""

    course_id = f"{parsed.department_code}-{parsed.course_number}"
    provenance = dict(parsed.provenance)
    provenance.setdefault("department_code", source_id)
    provenance.setdefault("course_number", source_id)
    return NormalizedCourse(
        course_id=course_id,
        campus=CAMPUS,
        department_code=parsed.department_code,
        course_number=parsed.course_number,
        title=parsed.title,
        description=parsed.description,
        credits=parsed.credits,
        prerequisites=parsed.prerequisites,
        corequisites=parsed.corequisites,
        source_field_provenance=provenance,
        freshness_metadata={"snapshot_id": snapshot_id, "source_id": source_id},
    )


def normalize_courses(
    parsed: Iterable[ParsedCourse], snapshot_id: str, source_id: str
) -> list[NormalizedCourse]:
    """Normalize parsed courses, enforcing course_id format and seattle campus."""

    return [normalize_course(item, snapshot_id, source_id) for item in parsed]
