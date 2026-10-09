"""Query intent classification node; see classify_query for routing policy."""

from __future__ import annotations

import re
from typing import Any

from courseagent.agents.schemas import QueryIntent, QueryIntentType


_COURSE_CODE_RE = re.compile(r"^\s*([A-Za-z&]{2,6})\s+(\d{3})(?:\s+[A-Za-z])?\s*$")
_COURSE_INFORMATION_RE = re.compile(
    r"show\s+me\s+information\s+about\s+(?:the\s+)?([A-Za-z&]{2,6})\s+(\d{3})",
    re.IGNORECASE,
)
_DEPT_SUFFIX_RE = re.compile(r"^\s*([A-Za-z&]{2,6})\s+(?:courses?|classes?|dept|department)\s*$", re.IGNORECASE)
_KNOWN_DEPTS = {"CSE", "INFO", "MATH", "PHYS", "CHEM", "BIOL", "ENGL", "ECON", "PSYCH", "STAT"}


def _heuristic_intent(query: str) -> QueryIntent:
    """Deterministic fallback classifier (no LLM dependency)."""

    stripped = query.strip()
    upper = stripped.upper()

    code_match = _COURSE_CODE_RE.match(stripped)
    information_match = _COURSE_INFORMATION_RE.fullmatch(stripped)
    if code_match or (
        information_match and information_match.group(1).upper() in _KNOWN_DEPTS
    ):
        match = code_match or information_match
        dept, number = match.group(1).upper(), match.group(2)
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

    Standalone codes and full queries matching "show me information about
    [the] <department> <number>" use deterministic lookup even with an LLM
    client. The prose form requires a known department and whitespace between
    the department and number; matching is case-insensitive. Other queries use
    the client when provided, with heuristic fallback.
    """

    heuristic = _heuristic_intent(query)
    if heuristic.intent == QueryIntentType.exact_code or llm is None:
        return heuristic
    try:
        structured_llm = llm.with_structured_output(QueryIntent)
        result = structured_llm.invoke(
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
        # An empty/malformed structured response is also a model failure.
        intent = QueryIntent.model_validate(result)
        if intent.intent == QueryIntentType.exact_code:
            course_id = (intent.course_id or "").strip()
            if not course_id:
                department = (intent.department_code or "").strip()
                number = (intent.course_number or "").strip()
                course_id = f"{department} {number}"
            code_match = _COURSE_CODE_RE.fullmatch(course_id.replace("-", " "))
            if not code_match:
                return _heuristic_intent(query)
            intent.course_id = f"{code_match.group(1).upper()}-{code_match.group(2)}"
        required_field = {
            QueryIntentType.department: "department_code",
            QueryIntentType.keyword: "keyword",
        }.get(intent.intent)
        if required_field:
            value = (getattr(intent, required_field) or "").strip()
            if not value:
                return _heuristic_intent(query)
            setattr(intent, required_field, value)
        return intent
    except Exception:  # noqa: BLE001 - fall back to deterministic path
        return _heuristic_intent(query)
