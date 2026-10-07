"""Tests for UW course catalog HTML parsing."""

from __future__ import annotations

from courseagent.dataflows.parsers.uw_course_catalog import parse_uw_course_catalog

CATALOG_HTML = """
<html><body>
<div class="course">
  <p>CSE 142</p>
  <p>Computer Programming I</p>
  <p>Basic programming-in-the-small abilities and concepts.</p>
</div>
<div class="course">
  <p>CSE 143</p>
  <p>Computer Programming II</p>
  <p>Continuation of CSE 142.</p>
</div>
</body></html>
"""


def test_parse_catalog_extracts_course_codes() -> None:
    courses = parse_uw_course_catalog(CATALOG_HTML, {"source_document_id": "doc-1"})
    assert len(courses) == 2
    assert courses[0].department_code == "CSE"
    assert courses[0].course_number == "142"
    assert courses[1].department_code == "CSE"
    assert courses[1].course_number == "143"


def test_parse_catalog_attaches_description_provenance() -> None:
    courses = parse_uw_course_catalog(CATALOG_HTML, {"source_document_id": "doc-1"})
    assert courses[0].description is not None
    assert "programming-in-the-small" in courses[0].description
    assert courses[0].provenance.get("description") == "doc-1"


def test_parse_empty_html_returns_no_courses() -> None:
    assert parse_uw_course_catalog("<html><body></body></html>") == []
