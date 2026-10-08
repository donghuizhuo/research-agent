"""Tests for query understanding and conditional routing."""

from __future__ import annotations

import pytest

from courseagent.agents.query_understanding import classify_query
from courseagent.agents.schemas import QueryIntent, QueryIntentType
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


@pytest.mark.parametrize("query", [
    "show me information about the cse 143",
    "Tell me about CSE143.",
    "What are the prerequisites for (CsE-143)?",
    "Show me CSE\t 143!",
    "CSE-143", "cse143", "CSE 143 A",
    "CSE 143: more information about CSE143, please.",
    "What is INFO 201?", "What is MATH 124?",
])
def test_explicit_reference_routes_to_exact_lookup(query) -> None:
    intent = classify_query(query)
    assert intent.intent == QueryIntentType.exact_code
    assert intent.course_id == f"{intent.department_code}-{intent.course_number}"
    assert route({"intent": intent}) == "exact_code_retriever"


@pytest.mark.parametrize("query", [
    "show me information about 143", "show me THE 143",
    "show me XCSE143", "show me _CSE143", "show me CSE1430",
    "show me CSE 1430", "show me CSE143abc", "show me CSE 143abc",
    "show me CSE 14", "show me CSE 143_", "show me TCSE 143",
    "Compare CSE 142 and CSE 143", "CSE143 or INFO201?",
    "Compare CSE 142 and 143", "CSE143/142", "142 versus CSE 143",
    "CSE 143 or CSS 143", "Compare CSE143 and CSS144",
    "intro programming courses", "machine learning", "CSE courses",
])
def test_non_unique_or_misleading_reference_does_not_force_exact_lookup(query) -> None:
    assert classify_query(query).intent != QueryIntentType.exact_code


def test_explicit_reference_is_deterministic_with_llm() -> None:
    class UnusedLLM:
        def with_structured_output(self, schema):
            pytest.fail("An explicit course reference must not depend on a model")

    assert classify_query("show me information about the cse 143", UnusedLLM()).course_id == "CSE-143"


def test_multi_course_query_keeps_existing_model_path() -> None:
    class AmbiguousLLM:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            return QueryIntent(intent=QueryIntentType.ambiguous)

    intent = classify_query("Compare CSE 142 and CSE 143", AmbiguousLLM())
    assert route({"intent": intent}) == "clarifier"
