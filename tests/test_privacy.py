"""Tests for sensitive-input redaction."""

from __future__ import annotations

from courseagent.agents.grounding import redact_sensitive_input


def test_redacts_student_number() -> None:
    assert redact_sensitive_input("lookup 1234567") == "lookup [REDACTED]"


def test_redacts_email() -> None:
    assert "user@uw.edu" not in redact_sensitive_input("email user@uw.edu")


def test_redacts_netid() -> None:
    result = redact_sensitive_input("my netid: jsmith42")
    assert "jsmith42" not in result


def test_preserves_normal_query() -> None:
    query = "what are the prerequisites for CSE 143"
    assert redact_sensitive_input(query) == query
