"""API integration test: POST /course-search returns citations + freshness."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from courseagent.api.app import create_app
from courseagent.dataflows.db import create_snapshot, init_db
from courseagent.dataflows.indexer import index_courses
from courseagent.dataflows.normalizer import normalize_courses
from courseagent.dataflows.parsers.uw_course_catalog import ParsedCourse
from courseagent.dataflows.source_registry import SourceRegistryEntry, register_source
from config.default_config import DefaultConfig


@pytest.fixture()
def client(tmp_path):
    conn = init_db(tmp_path / "db.sqlite3")
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
    index_courses(
        conn,
        normalize_courses(parsed, "snap-1", "uw_cse_catalog"),
        snapshot_id="snap-1",
        source_id="uw_cse_catalog",
        source_title="UW CSE Catalog",
        url="https://www.washington.edu/students/crscat/cse.html",
        source_document_id="doc-1",
        retrieved_at="2026-10-06T00:00:00+00:00",
    )
    app = create_app(DefaultConfig(data_dir=tmp_path, db_path=tmp_path / "db.sqlite3", sources_path=tmp_path / "sources.yml"))
    with TestClient(app) as test_client:
        yield test_client
    conn.close()


def test_course_search_returns_citation_and_freshness(client) -> None:
    response = client.post("/course-search", json={"query": "CSE 142"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer_type"] == "direct_answer"
    assert data["results"], "expected at least one result"
    result = data["results"][0]
    assert result["course_id"] == "CSE-142"
    assert result["citations"], "expected citations"
    assert any(c["claim_field"] == "title" for c in result["citations"])


def test_course_search_missing_returns_no_results(client) -> None:
    response = client.post("/course-search", json={"query": "CSE 999"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer_type"] == "no_results"


def test_course_detail_returns_citations(client) -> None:
    response = client.get("/courses/CSE-142")
    assert response.status_code == 200
    data = response.json()
    assert data["course_id"] == "CSE-142"
    assert data["citations"]
