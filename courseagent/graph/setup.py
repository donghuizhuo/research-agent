"""LangGraph StateGraph construction for the course research workflow."""

from __future__ import annotations

import sqlite3
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from courseagent.agents import answer_composer, clarifier, query_understanding, retrievers
from courseagent.agents.grounding import verify_grounding
from courseagent.agents.state import CourseResearchState
from courseagent.graph.conditional_logic import route


def setup_graph(
    conn: sqlite3.Connection,
    quick_llm: Any | None = None,
    deep_llm: Any | None = None,
) -> Any:
    """Build the course research StateGraph."""

    graph = StateGraph(CourseResearchState)

    def query_understanding_node(state: dict[str, Any]) -> dict[str, Any]:
        query = state.get("query", "")
        if "[REDACTED]" in query and not query.replace("[REDACTED]", "").strip():
            return {"intent": None, "interpreted_filters": {}, "status": "not_found"}
        intent = query_understanding.classify_query(query, quick_llm)
        return {"intent": intent, "interpreted_filters": {}}

    # Retrieval nodes receive the shared DB connection and LLMs via closure.
    def make_retriever(func: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def node(state: dict[str, Any]) -> dict[str, Any]:
            enriched = dict(state)
            enriched["conn"] = conn
            enriched["deep_llm"] = deep_llm
            enriched["quick_llm"] = quick_llm
            return func(enriched)

        return node

    def answer_node(state: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(state)
        enriched["conn"] = conn
        enriched["deep_llm"] = deep_llm
        return answer_composer.compose_answer(enriched)

    graph.add_node("query_understanding", query_understanding_node)
    graph.add_node("exact_code_retriever", make_retriever(retrievers.exact_code_retriever))
    graph.add_node("department_retriever", make_retriever(retrievers.department_retriever))
    graph.add_node("keyword_retriever", make_retriever(retrievers.keyword_retriever))
    graph.add_node("natural_language_retriever", make_retriever(retrievers.natural_language_retriever))
    graph.add_node("clarifier", clarifier.clarifier)
    graph.add_node("out_of_scope_responder", clarifier.out_of_scope_responder)
    graph.add_node("answer_composer", answer_node)
    graph.add_node("grounding_verifier", verify_grounding)

    graph.add_edge(START, "query_understanding")
    graph.add_conditional_edges(
        "query_understanding",
        lambda state: "answer_composer" if state.get("status") == "not_found" else route(state),
        {
            "answer_composer": "answer_composer",
            "exact_code_retriever": "exact_code_retriever",
            "department_retriever": "department_retriever",
            "keyword_retriever": "keyword_retriever",
            "natural_language_retriever": "natural_language_retriever",
            "clarifier": "clarifier",
            "out_of_scope_responder": "out_of_scope_responder",
        },
    )
    graph.add_edge("exact_code_retriever", "answer_composer")
    graph.add_edge("department_retriever", "answer_composer")
    graph.add_edge("keyword_retriever", "answer_composer")
    graph.add_edge("natural_language_retriever", "answer_composer")
    graph.add_edge("answer_composer", "grounding_verifier")
    graph.add_edge("grounding_verifier", END)
    graph.add_edge("clarifier", END)
    graph.add_edge("out_of_scope_responder", END)

    return graph
