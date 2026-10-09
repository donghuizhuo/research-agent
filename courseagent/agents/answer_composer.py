"""Grounded answer composition node (deep-tier LLM)."""

from __future__ import annotations

from typing import Any

from courseagent.agents.schemas import CourseAnswer, CourseSearchResult, render_course_result


def _compose_without_llm(state: dict[str, Any]) -> CourseAnswer:
    courses = [CourseSearchResult(**c) if isinstance(c, dict) else c for c in state.get("retrieved_courses", [])]
    query = state.get("query", "")
    if not courses:
        return CourseAnswer(
            query=query,
            answer="No matching course found in approved indexed sources.",
            limitations=list(state.get("limitations", [])),
            status=state.get("status", "not_found"),
            workflow_id=state.get("workflow_id"),
        )
    if len(courses) == 1:
        course = courses[0]
        answer = render_course_result(course)
        return CourseAnswer(
            query=query,
            answer=answer,
            course=course,
            citations=course.citations,
            limitations=list(state.get("limitations", [])),
            status=state.get("status", "ok"),
            workflow_id=state.get("workflow_id"),
        )
    answer = "\n\n".join(render_course_result(c) for c in courses)
    return CourseAnswer(
        query=query,
        answer=answer,
        ranked_courses=courses,
        citations=[c for course in courses for c in course.citations],
        limitations=list(state.get("limitations", [])),
        status=state.get("status", "ok"),
        workflow_id=state.get("workflow_id"),
    )


def compose_answer(state: dict[str, Any]) -> dict[str, Any]:
    """Compose the catalog answer with optional, unverified model prose."""

    # Catalog objects and their provenance always come from retrieval. Generated
    # prose is separate and cannot replace this authoritative typed answer.
    answer = _compose_without_llm(state)
    llm = state.get("deep_llm")
    if llm is None or not state.get("retrieved_courses"):
        return {"structured_answer": answer, "answer": answer.answer}

    courses = state.get("retrieved_courses", [])
    citations = state.get("citations", [])
    prompt = (
        "You are a UW Seattle course research assistant. Answer ONLY using the "
        "provided retrieved course facts and citations. Do not invent facts. "
        "Attach a citation to each substantive claim. If a fact is unavailable, "
        "state it as a limitation. Never assert live enrollment, seats, or "
        "registration status.\n\n"
        f"Retrieved courses:\n{courses}\n\nCitations:\n{citations}\n\n"
        f"User query: {state.get('query', '')}"
    )
    try:
        raw = llm.invoke(prompt)
        text = raw.content if hasattr(raw, "content") else raw
        if isinstance(text, str) and text.strip():
            return {"structured_answer": answer, "answer": text}
    except Exception:  # noqa: BLE001 - fall back to deterministic rendering
        pass
    return {"structured_answer": answer, "answer": answer.answer}
