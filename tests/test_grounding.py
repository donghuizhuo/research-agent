"""Tests for grounding, conflict detection, and quarter availability."""

from __future__ import annotations

from courseagent.agents.grounding import (
    detect_conflicts,
    has_quarter_confirmation,
    verify_grounding,
)
from courseagent.agents.schemas import Citation


def test_verify_grounding_flags_uncited_courses() -> None:
    state = {
        "retrieved_courses": [{"course_id": "CSE-142"}],
        "citations": [],
        "limitations": [],
    }
    result = verify_grounding(state)
    assert any("no per-field citations" in item for item in result["limitations"])


def test_verify_grounding_passes_cited_courses() -> None:
    state = {
        "retrieved_courses": [{"course_id": "CSE-142"}],
        "citations": [Citation(citation_id="c1", course_id="CSE-142", claim_field="title", evidence_text="Computer Programming I", url="http://x")],
        "limitations": [],
    }
    result = verify_grounding(state)
    assert result["limitations"] == []


def test_detect_conflicts_across_sources() -> None:
    citations = [
        Citation(citation_id="c1", course_id="CSE-142", claim_field="credits", evidence_text="4", url="http://a"),
        Citation(citation_id="c2", course_id="CSE-142", claim_field="credits", evidence_text="5", url="http://b"),
    ]
    conflicts = detect_conflicts([], citations)
    assert len(conflicts) == 1
    assert conflicts[0]["field"] == "credits"
    assert conflicts[0]["status"] == "open"


def test_detect_conflicts_no_conflict() -> None:
    citations = [
        Citation(citation_id="c1", course_id="CSE-142", claim_field="credits", evidence_text="4", url="http://a"),
        Citation(citation_id="c2", course_id="CSE-142", claim_field="credits", evidence_text="4", url="http://b"),
    ]
    assert detect_conflicts([], citations) == []


def test_quarter_confirmation_always_false_without_data() -> None:
    assert not has_quarter_confirmation({"course_id": "CSE-142"}, "autumn")


def test_quarter_confirmation_requires_quarters_offered() -> None:
    course = {"course_id": "CSE-142", "quarters_offered": ["autumn"]}
    assert has_quarter_confirmation(course, "autumn")
    assert not has_quarter_confirmation(course, "winter")
