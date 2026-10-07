"""Tests for deterministic retrieval over SQLite/FTS5."""

from __future__ import annotations

import pytest

from courseagent.dataflows.db import create_snapshot, init_db
from courseagent.dataflows.indexer import index_courses
from courseagent.dataflows.normalizer import normalize_courses
from courseagent.dataflows.parsers.uw_course_catalog import ParsedCourse
from courseagent.dataflows.source_registry import SourceRegistry, SourceRegistryEntry, register_source
from courseagent.dataflows import retrieval


def _catalog_entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
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
    )


@pytest.fixture()
def seeded_db(tmp_path):
    conn = init_db(tmp_path / "test.sqlite3")
    register_source(conn, _catalog_entry())
    create_snapshot(conn, "snap-1", ["uw_cse_catalog"], status="indexed")
    parsed = [
        ParsedCourse(department_code="CSE", course_number="142", title="Computer Programming I", description="Basic programming."),
        ParsedCourse(department_code="CSE", course_number="143", title="Computer Programming II", description="Data structures."),
        ParsedCourse(department_code="INFO", course_number="200", title="Intellectual Foundations", description="Information systems."),
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
    yield conn
    conn.close()


def test_find_course_by_code(seeded_db) -> None:
    row = retrieval.find_course_by_code(seeded_db, "CSE-142")
    assert row is not None
    assert row["title"] == "Computer Programming I"


def test_find_course_by_code_case_insensitive(seeded_db) -> None:
    assert retrieval.find_course_by_code(seeded_db, "cse-143") is not None


def test_find_course_missing(seeded_db) -> None:
    assert retrieval.find_course_by_code(seeded_db, "CSE-999") is None


def test_search_department(seeded_db) -> None:
    rows = retrieval.search_department(seeded_db, "CSE")
    assert len(rows) == 2


def test_search_keyword(seeded_db) -> None:
    rows = retrieval.search_keyword(seeded_db, "programming")
    assert len(rows) >= 1


def test_search_natural_language(seeded_db) -> None:
    rows = retrieval.search_natural_language(seeded_db, "introductory programming course")
    assert len(rows) >= 1
