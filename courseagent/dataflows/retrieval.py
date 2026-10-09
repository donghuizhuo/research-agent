"""Deterministic retrieval over SQLite/FTS5."""

from __future__ import annotations

import sqlite3
from typing import Any

from courseagent.dataflows.db import row_to_dict


def _course_from_row(row: sqlite3.Row) -> dict[str, Any]:
    data = row_to_dict(row)
    if data is None:
        raise ValueError("Expected a course row")
    return data


def find_course_by_code(conn: sqlite3.Connection, course_id: str) -> dict[str, Any] | None:
    """Exact lookup by normalized course_id (e.g. CSE-142)."""

    cursor = conn.execute("SELECT * FROM courses WHERE course_id = ?", (course_id.upper(),))
    row = cursor.fetchone()
    return _course_from_row(row) if row is not None else None


def fetch_citations(conn: sqlite3.Connection, course_id: str) -> list[dict[str, Any]]:
    cursor = conn.execute("SELECT * FROM citations WHERE course_id = ? ORDER BY claim_field", (course_id,))
    return [dict(row) for row in cursor.fetchall()]


def search_department(conn: sqlite3.Connection, department_code: str, limit: int = 25) -> list[dict[str, Any]]:
    cursor = conn.execute(
        "SELECT * FROM courses WHERE department_code = ? ORDER BY course_number LIMIT ?",
        (department_code.upper(), limit),
    )
    return [dict(row) for row in cursor.fetchall()]


def search_keyword(conn: sqlite3.Connection, keyword: str, limit: int = 25) -> list[dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT c.*, s.title AS match_title, bm25(search_documents_fts) AS rank
        FROM search_documents_fts
        JOIN search_documents s ON s.rowid = search_documents_fts.rowid
        LEFT JOIN courses c ON c.course_id = s.course_id
        WHERE search_documents_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        ('"' + keyword.replace('"', '""') + '"', limit),
    )
    return [dict(row) for row in cursor.fetchall()]


def search_natural_language(
    conn: sqlite3.Connection, query: str, limit: int = 25
) -> list[dict[str, Any]]:
    """Tokenize a natural-language query and run FTS5 over search documents.

    FTS5 requires its own query syntax; raw natural language often contains
    stopwords and punctuation, so we extract bare alphanumeric tokens and OR
    them. This keeps the retriever deterministic and grounded (no vector index
    required for the MVP).
    """

    import re

    stopwords = {
        "a", "an", "the", "and", "or", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "to", "about", "course", "courses",
        "class", "classes", "what", "which", "how", "intro", "introductory",
    }
    tokens = [t for t in re.findall(r"[A-Za-z0-9]{2,}", query.lower()) if t not in stopwords]
    if not tokens:
        return []
    fts_query = " OR ".join(tokens)
    cursor = conn.execute(
        """
        SELECT c.*, s.title AS match_title, bm25(search_documents_fts) AS rank
        FROM search_documents_fts
        JOIN search_documents s ON s.rowid = search_documents_fts.rowid
        LEFT JOIN courses c ON c.course_id = s.course_id
        WHERE search_documents_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (fts_query, limit),
    )
    return [dict(row) for row in cursor.fetchall()]
