"""Tests for query understanding and conditional routing."""

from __future__ import annotations

from courseagent.agents.query_understanding import classify_query
from courseagent.agents.schemas import QueryIntentType
from courseagent.graph.conditional_logic import route


def test_exact_code_classification() -> None:
    intent = classify_query("CSE 142")
    assert intent.intent == QueryIntentType.exact_code
    assert intent.course_id == "CSE-142"


def test_department_classification() -> None:
    intent = classify_query("CSE courses")
    assert intent.intent == QueryIntentType.department
    assert intent.department_code == "CSE"


def test_bare_department_code() -> None:
    intent = classify_query("INFO")
    assert intent.intent == QueryIntentType.department
    assert intent.department_code == "INFO"


def test_multiword_phrase_is_natural_language() -> None:
    intent = classify_query("machine learning")
    assert intent.intent == QueryIntentType.natural_language


def test_single_keyword() -> None:
    intent = classify_query("algorithms")
    assert intent.intent == QueryIntentType.keyword


def test_exact_code_with_section_suffix() -> None:
    intent = classify_query("CSE 142 A")
    assert intent.intent == QueryIntentType.exact_code
    assert intent.course_id == "CSE-142"


def test_route_exact_code() -> None:
    intent = classify_query("CSE 142")
    assert route({"intent": intent}) == "exact_code_retriever"


def test_route_department() -> None:
    intent = classify_query("INFO courses")
    assert route({"intent": intent}) == "department_retriever"


def test_route_out_of_scope_default() -> None:
    assert route({"intent": "out_of_scope"}) == "out_of_scope_responder"
