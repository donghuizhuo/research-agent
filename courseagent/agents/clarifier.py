"""Ambiguity clarification and out-of-scope responder nodes."""

from __future__ import annotations

from typing import Any


def clarifier(state: dict[str, Any]) -> dict[str, Any]:
    """Produce a follow-up question for ambiguous queries."""

    query = state.get("query", "")
    return {
        "needs_clarification": True,
        "answer": f"Could you clarify your query '{query}'? For example, provide an exact course code like CSE 142, a department like INFO, or a specific topic.",
        "limitations": ["Ambiguous query; clarification requested before retrieval."],
        "status": "needs_clarification",
    }


def out_of_scope_responder(state: dict[str, Any]) -> dict[str, Any]:
    """Return a labeled limitation for out-of-scope or non-course requests."""

    query = state.get("query", "")
    return {
        "answer": (
            f"'{query}' is outside the v1 scope of the UW Seattle course research agent. "
            "This agent only searches approved indexed/snapshot UW Seattle course information; "
            "it does not provide live enrollment, seat availability, registration status, or "
            "real-time schedule data."
        ),
        "limitations": ["Out-of-scope or non-course query; no structured retrieval performed."],
        "status": "out_of_scope",
    }
