"""Deterministic routing from classified query intent to graph nodes."""

from __future__ import annotations

from typing import Any

from courseagent.agents.schemas import QueryIntent, QueryIntentType


def route(state: dict[str, Any]) -> str:
    """Return the target node name based on state['intent'].

    Supports both QueryIntent objects and raw strings for robustness.
    """

    intent = state.get("intent")
    if isinstance(intent, QueryIntent):
        value = intent.intent.value if hasattr(intent.intent, "value") else str(intent.intent)
    else:
        value = str(intent or "")

    mapping = {
        QueryIntentType.exact_code.value: "exact_code_retriever",
        QueryIntentType.department.value: "department_retriever",
        QueryIntentType.keyword.value: "keyword_retriever",
        QueryIntentType.natural_language.value: "natural_language_retriever",
        QueryIntentType.ambiguous.value: "clarifier",
        QueryIntentType.out_of_scope.value: "out_of_scope_responder",
    }
    return mapping.get(value, "out_of_scope_responder")
