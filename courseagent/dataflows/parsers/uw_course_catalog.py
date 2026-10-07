"""Parser for UW course catalog HTML pages (Tier 1 normalized facts)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup


@dataclass
class ParsedCourse:
    department_code: str
    course_number: str
    title: str | None = None
    description: str | None = None
    credits: str | None = None
    prerequisites: str | None = None
    corequisites: str | None = None
    provenance: dict[str, str] = field(default_factory=dict)


_COURSE_CODE_RE = re.compile(r"^\s*([A-Z&]{2,6})\s+(\d{3})\s*$")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _match_course_line(text: str) -> tuple[str, str] | None:
    match = _COURSE_CODE_RE.match(text.strip())
    if not match:
        return None
    return match.group(1).upper(), match.group(2)


def parse_uw_course_catalog(html: str, source_doc: dict[str, Any] | None = None) -> list[ParsedCourse]:
    """Extract course records from a UW catalog HTML page.

    UW course catalog pages are `<div>`-heavy; this parser walks text blocks and
    associates course codes with the trailing description text. It is deliberately
    conservative: every extracted field carries a provenance reference.
    """

    soup = BeautifulSoup(html, "html.parser")
    courses: list[ParsedCourse] = []
    source_ref = (source_doc or {}).get("source_document_id", "catalog")
    current: ParsedCourse | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal current, buffer
        if current is None:
            buffer = []
            return
        text = _clean(" ".join(buffer))
        buffer = []
        if text:
            current.description = text
            current.provenance["description"] = source_ref
        courses.append(current)
        current = None

    for element in soup.find_all(["p", "div", "li", "td"]):
        if element.find(["p", "div", "li"]):
            continue  # skip nested containers; iterate leaves
        text = element.get_text(" ", strip=True)
        if not text:
            continue
        code_match = _match_course_line(text)
        if code_match and len(text.strip().split()) == 2:
            flush()
            dept, number = code_match
            current = ParsedCourse(
                department_code=dept,
                course_number=number,
                provenance={"department_code": source_ref, "course_number": source_ref},
            )
            continue
        if current is not None:
            buffer.append(text)

    flush()
    return courses
