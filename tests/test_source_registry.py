"""Tests for source registry allowlist checks and URL approval."""

from __future__ import annotations

import pytest

from courseagent.dataflows.source_registry import (
    SourceRegistry,
    SourceRegistryEntry,
    is_url_approved,
    load_source_registry,
)


def make_registry() -> SourceRegistry:
    return SourceRegistry(
        [
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
            SourceRegistryEntry(
                id="allen_school",
                name="Allen School",
                tier=2,
                type="department",
                authority="official",
                department="CSE",
                url="https://www.cs.washington.edu/",
                allowed_url_patterns=("https://www.cs.washington.edu/*",),
                extraction_policy="supporting_context_by_default",
                promotion_rule="clearly_structured_and_directly_cited_only",
            ),
        ]
    )


def test_is_url_approved_exact_match() -> None:
    registry = make_registry()
    assert is_url_approved("https://www.washington.edu/students/crscat/cse.html", registry)


def test_is_url_approved_wildcard() -> None:
    registry = make_registry()
    assert is_url_approved("https://www.cs.washington.edu/people", registry)


def test_is_url_approved_rejects_unapproved() -> None:
    registry = make_registry()
    assert not is_url_approved("https://evil.example.com/cse.html", registry)


def test_load_source_registry_from_yaml(tmp_path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(
        """
sources:
  - id: uw_cse_catalog
    name: UW CSE Catalog
    tier: 1
    type: course_catalog
    authority: official
    department: CSE
    url: https://www.washington.edu/students/crscat/cse.html
    allowed_url_patterns:
      - https://www.washington.edu/students/crscat/cse.html
    extraction_policy: normalized_facts_allowed
""",
        encoding="utf-8",
    )
    registry = load_source_registry(path)
    assert registry.get("uw_cse_catalog").tier == 1
    assert registry.get("uw_cse_catalog").department == "CSE"


def test_unknown_source_raises() -> None:
    registry = make_registry()
    with pytest.raises(KeyError):
        registry.get("nope")
