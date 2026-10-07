"""Tests for UW course catalog HTML parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

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


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("department,count", [("cse", 6), ("info", 5)])
def test_real_catalog_paragraphs(department, count):
    courses = parse_uw_course_catalog(
        (FIXTURES / f"uw_{department}_catalog.html").read_text(),
        {"source_document_id": "actual-doc"},
    )
    assert len(courses) == count
    assert all(c.department_code == department.upper() for c in courses)
    for course in courses:
        assert course.title and course.credits and course.description
        assert "MyPlan" not in course.description
        assert course.title not in course.description
        assert set(course.provenance.values()) == {"actual-doc"}
        for field in ("title", "description", "credits", "prerequisites", "corequisites"):
            assert (field in course.provenance) == (getattr(course, field) is not None)
    by_number = {c.course_number: c for c in courses}
    if department == "cse":
        assert by_number["112"].title == "Advanced Placement (AP) Computer Science A"
        assert by_number["142"].title == "Computer Programming I"
        assert by_number["143"].prerequisites == "CSE 142."
        assert by_number["142"].prerequisites is None
        assert by_number["599"].credits == "1-5, max. 30"
        assert by_number["600"].credits == "*-"
        assert by_number["700"].credits == "*-"
    else:
        assert by_number["198"].credits == "1-5, max. 15"
        assert by_number["340"].prerequisites == "either CSE 123, CSE 143, CSE 154, or CSE 163; and INFO 201."


def test_catalog_boundaries_missing_fields_and_inline_markup():
    html = '''<div>
    <p><b>CSE 142 Computer Programming I (4)</b><br>Arrays &amp; objects.</p>
    <p><b>INFO 20 Invalid number (5)</b><br>Never attach this.</p>
    <p><b>INFO 201 Missing credits</b><br>Never attach this either.</p>
    <p><b>INFO 202 (5)</b><br>Missing title.</p>
    <p><strong>INFO 200 <em>Informatics</em> (5)</strong></p>
    <p><b>CSE 143 Computer Programming II (5)</b><br>Continuation.
    Prerequisite: CSE 142. Corequisite: MATH 124. Offered: A.
    <a href="https://myplan.washington.edu/">View course details in MyPlan: CSE 143</a></p>
    <p>Footer: CSE 999 should not be indexed.</p></div>'''
    courses = parse_uw_course_catalog(html, {"source_document_id": "doc"})
    assert [c.course_number for c in courses] == ["142", "200", "143"]
    assert courses[0].description == "Arrays & objects."
    assert courses[1].title == "Informatics"
    assert courses[1].description is None
    assert "description" not in courses[1].provenance
    assert courses[2].prerequisites == "CSE 142."
    assert courses[2].corequisites == "MATH 124."
    assert "Footer" not in courses[2].description
