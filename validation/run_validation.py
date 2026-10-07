"""Run golden validation cases against a seeded database and report pass/fail."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from courseagent.dataflows.db import create_snapshot, init_db
from courseagent.dataflows.indexer import index_courses
from courseagent.dataflows.normalizer import normalize_courses
from courseagent.dataflows.parsers.uw_course_catalog import ParsedCourse
from courseagent.dataflows.source_registry import SourceRegistryEntry, register_source
from courseagent.graph.course_graph import CourseResearchGraph
from config.default_config import DefaultConfig

SEED_COURSES = [
    ParsedCourse(department_code="CSE", course_number="142", title="Computer Programming I", description="Basic programming-in-the-small abilities and concepts.", credits="4"),
    ParsedCourse(department_code="CSE", course_number="143", title="Computer Programming II", description="Data structures and algorithms.", credits="5"),
    ParsedCourse(department_code="INFO", course_number="200", title="Intellectual Foundations", description="Information systems and society.", credits="5"),
]


def _seed(tmp_path: Path) -> DefaultConfig:
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
    index_courses(
        conn,
        normalize_courses(SEED_COURSES, "snap-1", "uw_cse_catalog"),
        snapshot_id="snap-1",
        source_id="uw_cse_catalog",
        source_title="UW CSE Catalog",
        url="https://www.washington.edu/students/crscat/cse.html",
        source_document_id="doc-1",
        retrieved_at="2026-10-06T00:00:00+00:00",
    )
    conn.close()
    return DefaultConfig(data_dir=tmp_path, db_path=tmp_path / "db.sqlite3")


def _check(case: dict, result: dict) -> list[str]:
    expect = case.get("expect", {})
    failures: list[str] = []
    for key, value in expect.items():
        if key in ("answer_contains", "has_citation", "has_freshness", "has_results", "has_limitation", "never_authoritative", "workflow_id"):
            continue
        if result.get(key) != value:
            failures.append(f"{key}: expected {value!r}, got {result.get(key)!r}")
    if "answer_contains" in expect:
        answer = result.get("answer") or ""
        for needle in expect["answer_contains"]:
            if needle not in answer:
                failures.append(f"answer missing {needle!r}")
    if expect.get("has_citation") and not result.get("citations"):
        failures.append("expected citations, got none")
    if expect.get("has_freshness") and not result.get("freshness"):
        failures.append("expected freshness metadata, got none")
    if expect.get("has_results") and not result.get("structured_answer"):
        failures.append("expected results")
    if expect.get("has_limitation") and not result.get("limitations"):
        failures.append("expected limitation message")
    if expect.get("workflow_id") and result.get("workflow_id") != expect["workflow_id"]:
        failures.append(f"workflow_id mismatch: {result.get('workflow_id')}")
    return failures


def main() -> int:
    cases_path = Path(__file__).parent / "golden-cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]

    with tempfile.TemporaryDirectory() as tmp:
        config = _seed(Path(tmp))
        graph = CourseResearchGraph(config=config)

        passed = 0
        for case in cases:
            result = graph.run(case["query"], workflow_id=case.get("workflow_id"))
            failures = _check(case, result)
            if failures:
                print(f"FAIL {case['id']}: {failures}")
            else:
                passed += 1
                print(f"PASS {case['id']}")

    total = len(cases)
    print(f"\n{passed}/{total} golden cases passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
