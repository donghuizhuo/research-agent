"""US1 integration test: exact course lookup through the full graph."""

from __future__ import annotations

import pytest

from courseagent.dataflows.db import create_snapshot, init_db
from courseagent.dataflows.indexer import index_courses
from courseagent.dataflows.normalizer import normalize_courses
from courseagent.dataflows.parsers.uw_course_catalog import ParsedCourse
from courseagent.dataflows.source_registry import SourceRegistry, SourceRegistryEntry, register_source
from courseagent.graph.course_graph import CourseResearchGraph
from config.default_config import DefaultConfig


@pytest.fixture()
def graph(tmp_path):
    conn = init_db(tmp_path / "test.sqlite3")
    register_source(
        conn,
        SourceRegistryEntry(
            id="uw_cse_catalog",
            name="UW CSE Catalog",
            tier=1,
            type="course_catalog",
            authority="official",
            department="CSE",
            url="https://www.washington.edu/students/crscat/cse.html",
            allowed_url_patterns=("https://www.washington.edu/students/crscat/cse.html",),
            extraction_policy="normalized_facts_allowed",
            promotion_rule=None,
        ),
    )
    create_snapshot(conn, "snap-1", ["uw_cse_catalog"], status="indexed")
    parsed = [
        ParsedCourse(
            department_code="CSE",
            course_number="142",
            title="Computer Programming I",
            description="Basic programming-in-the-small abilities and concepts.",
            credits="4",
        )
    ]
    courses = normalize_courses(parsed, snapshot_id="snap-1", source_id="uw_cse_catalog")
    index_courses(
        conn,
        courses,
        snapshot_id="snap-1",
        source_id="uw_cse_catalog",
        source_title="UW CSE Catalog",
        url="https://www.washington.edu/students/crscat/cse.html",
        source_document_id="doc-1",
        retrieved_at="2026-10-06T00:00:00+00:00",
    )
    config = DefaultConfig(data_dir=tmp_path, db_path=tmp_path / "test.sqlite3")
    return CourseResearchGraph(config=config, conn=conn)


def test_exact_lookup_returns_cited_answer(graph) -> None:
    result = graph.run("CSE 142", workflow_id="wf-1")
    assert result["status"] == "ok"
    assert "CSE 142" in result["answer"] or "Computer Programming" in result["answer"]
    assert result["citations"], "expected at least one citation"
    assert any(c["claim_field"] == "title" for c in result["citations"])
    assert result["workflow_id"] == "wf-1"


def test_missing_course_returns_limitation(graph) -> None:
    result = graph.run("CSE 999", workflow_id="wf-2")
    assert result["status"] == "not_found"
    assert result["limitations"], "expected a limitation message for a missing course"


def test_checkpoint_state_persists(tmp_path) -> None:
    """A second run with the same workflow_id resumes from checkpointed state."""

    conn = init_db(tmp_path / "check.sqlite3")
    register_source(
        conn,
        SourceRegistryEntry(
            id="uw_cse_catalog",
            name="UW CSE Catalog",
            tier=1,
            type="course_catalog",
            authority="official",
            department="CSE",
            url="https://www.washington.edu/students/crscat/cse.html",
            allowed_url_patterns=("https://www.washington.edu/students/crscat/cse.html",),
            extraction_policy="normalized_facts_allowed",
            promotion_rule=None,
        ),
    )
    create_snapshot(conn, "snap-1", ["uw_cse_catalog"], status="indexed")
    parsed = [ParsedCourse(department_code="CSE", course_number="142", title="Computer Programming I", description="Intro.")]
    index_courses(
        conn,
        normalize_courses(parsed, snapshot_id="snap-1", source_id="uw_cse_catalog"),
        snapshot_id="snap-1",
        source_id="uw_cse_catalog",
        source_title="UW CSE Catalog",
        url="https://www.washington.edu/students/crscat/cse.html",
        source_document_id="doc-1",
        retrieved_at="2026-10-06T00:00:00+00:00",
    )
    config = DefaultConfig(data_dir=tmp_path, db_path=tmp_path / "check.sqlite3")
    g = CourseResearchGraph(config=config, conn=conn)
    first = g.run("CSE 142", workflow_id="wf-check")
    second = g.run("CSE 142", workflow_id="wf-check")
    assert first["workflow_id"] == second["workflow_id"] == "wf-check"
    assert (tmp_path / "checkpoints.sqlite3").exists()


def test_query_reset_keeps_history_but_clears_retrieval_and_flags(graph) -> None:
    from langchain_core.messages import HumanMessage
    from courseagent.graph.checkpointer import thread_id_for

    workflow = 'wf-reset-history'
    first = graph.run('CSE 142', workflow_id=workflow)
    app = graph.compile()
    config = {'configurable': {'thread_id': thread_id_for(workflow)}}
    app.update_state(config, {
        'messages': [HumanMessage(content='prior conversation')],
        'needs_clarification': True,
        'interpreted_filters': {'department': 'CSE'},
        'conflicts': [{'course_id': 'CSE-142', 'field': 'title'}],
    })
    missing = graph.run('CSE 999', workflow_id=workflow)
    assert first['workflow_id'] == missing['workflow_id'] == workflow
    assert missing['citations'] == missing['freshness'] == missing['conflicts'] == []
    assert missing['needs_clarification'] is False
    state = app.get_state(config).values
    assert state['retrieved_courses'] == []
    assert state['interpreted_filters'] == {}
    assert state['messages'][0].content == 'prior conversation'
    assert len(list(app.get_state_history(config))) > 1  # history was not deleted/replaced
