"""Query intent classification node (quick-tier LLM -> structured output)."""

from __future__ import annotations

import re
from typing import Any

from courseagent.agents.schemas import QueryIntent, QueryIntentType


_COURSE_CODE_RE = re.compile(r"^\s*([A-Za-z&]{2,6})(?:\s*-\s*|\s*)(\d{3})(?:\s+[A-Za-z])?\s*$")
_COURSE_REFERENCE_RE = re.compile(
    r"(?<![\w&])([A-Za-z&]{2,6})(?:\s*-\s*|\s*)(\d{3})(?![\w&])"
)
_DEPT_SUFFIX_RE = re.compile(r"^\s*([A-Za-z&]{2,6})\s+(?:courses?|classes?|dept|department)\s*$", re.IGNORECASE)
_KNOWN_DEPTS = {"CSE", "INFO", "MATH", "PHYS", "CHEM", "BIOL", "ENGL", "ECON", "PSYCH", "STAT"}


def _heuristic_intent(query: str) -> QueryIntent:
    """Deterministic fallback classifier (no LLM dependency)."""

    stripped = query.strip()
    upper = stripped.upper()

    # Keep standalone codes (including section letters) supported. In prose,
    # require a known department so phrases such as "about 143" aren't codes.
    # Multiple distinct references retain the existing discovery/LLM path.
    code_match = _COURSE_CODE_RE.match(stripped)
    references = {
        (match.group(1).upper(), match.group(2))
        for match in _COURSE_REFERENCE_RE.finditer(stripped)
    }
    reference = next(iter(references)) if len(references) == 1 else None
    # A second bare number can be a shorthand reference ("CSE 142 or 143").
    # Leave those requests on their existing path rather than choosing one.
    other_numbers = set(re.findall(r"(?<!\w)\d{3}(?!\w)", stripped))
    if code_match or (
        reference is not None
        and reference[0] in _KNOWN_DEPTS
        and other_numbers <= {reference[1]}
    ):
        dept, number = (
            (code_match.group(1).upper(), code_match.group(2))
            if code_match else reference
        )
        return QueryIntent(
            intent=QueryIntentType.exact_code,
            department_code=dept,
            course_number=number,
            course_id=f"{dept}-{number}",
            confidence=0.95,
            rationale="Deterministic course-code pattern match",
        )

    # Department-scoped query like "CSE courses" or "INFO classes".
    dept_match = _DEPT_SUFFIX_RE.match(stripped)
    if dept_match:
        return QueryIntent(
            intent=QueryIntentType.department,
            department_code=dept_match.group(1).upper(),
            confidence=0.9,
            rationale="Department token followed by a course/class suffix",
        )

    # Bare known department code.
    if upper in _KNOWN_DEPTS:
        return QueryIntent(
            intent=QueryIntentType.department,
            department_code=upper,
            confidence=0.85,
            rationale="Bare known department code",
        )

    if len(stripped.split()) == 1:
        return QueryIntent(
            intent=QueryIntentType.keyword,
            keyword=stripped,
            confidence=0.6,
            rationale="Single keyword token",
        )
    return QueryIntent(
        intent=QueryIntentType.natural_language,
        natural_language_query=stripped,
        confidence=0.5,
        rationale="Default natural-language interpretation",
    )


def classify_query(query: str, llm: Any | None = None) -> QueryIntent:
    """Classify a user query into a structured QueryIntent.

    Unambiguous explicit course codes use deterministic lookup even with an LLM
    client. Other queries use the client when provided, with heuristic fallback.
    """

    heuristic = _heuristic_intent(query)
    if heuristic.intent == QueryIntentType.exact_code or llm is None:
        return heuristic
    structured_llm = llm.with_structured_output(QueryIntent)
    try:
        return structured_llm.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "Classify a UW Seattle course search query. Return one of: "
                        "exact_code, department, keyword, natural_language, ambiguous, out_of_scope. "
                        "Never fabricate course facts."
                    ),
                },
                {"role": "user", "content": query},
            ]
        )
    except Exception:  # noqa: BLE001 - fall back to deterministic path
        return _heuristic_intent(query)
