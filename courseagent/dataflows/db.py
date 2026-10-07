"""SQLite connection management and schema initialization (FTS5)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tier INTEGER NOT NULL,
    type TEXT NOT NULL,
    authority TEXT NOT NULL,
    department TEXT,
    url TEXT,
    extraction_policy TEXT NOT NULL,
    promotion_rule TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    refresh_mode TEXT NOT NULL,
    source_ids TEXT NOT NULL,
    status TEXT NOT NULL,
    error_summary TEXT
);

CREATE TABLE IF NOT EXISTS source_documents (
    source_document_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    content_type TEXT,
    raw_content_ref TEXT,
    content_hash TEXT,
    retrieved_at TEXT,
    indexed_at TEXT,
    parse_status TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(id),
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(snapshot_id)
);

CREATE TABLE IF NOT EXISTS courses (
    course_id TEXT PRIMARY KEY,
    campus TEXT NOT NULL,
    department_code TEXT NOT NULL,
    course_number TEXT NOT NULL,
    title TEXT,
    description TEXT,
    credits TEXT,
    prerequisites TEXT,
    corequisites TEXT,
    source_field_provenance TEXT NOT NULL DEFAULT '{}',
    freshness_metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_documents (
    search_document_id TEXT PRIMARY KEY,
    source_document_id TEXT,
    course_id TEXT,
    department_code TEXT,
    document_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    freshness_metadata TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (source_document_id) REFERENCES source_documents(source_document_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_documents_fts USING fts5(
    title,
    body,
    content='search_documents',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS search_documents_ai AFTER INSERT ON search_documents BEGIN
    INSERT INTO search_documents_fts(rowid, title, body) VALUES (new.rowid, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS search_documents_ad AFTER DELETE ON search_documents BEGIN
    INSERT INTO search_documents_fts(search_documents_fts, rowid, title, body)
    VALUES ('delete', old.rowid, old.title, old.body);
END;

CREATE TRIGGER IF NOT EXISTS search_documents_au AFTER UPDATE ON search_documents BEGIN
    INSERT INTO search_documents_fts(search_documents_fts, rowid, title, body)
    VALUES ('delete', old.rowid, old.title, old.body);
    INSERT INTO search_documents_fts(rowid, title, body) VALUES (new.rowid, new.title, new.body);
END;

CREATE TABLE IF NOT EXISTS citations (
    citation_id TEXT PRIMARY KEY,
    source_document_id TEXT,
    course_id TEXT,
    claim_field TEXT,
    evidence_text TEXT NOT NULL,
    url TEXT NOT NULL,
    source_title TEXT,
    snapshot_id TEXT,
    retrieved_at TEXT,
    indexed_at TEXT,
    FOREIGN KEY (source_document_id) REFERENCES source_documents(source_document_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS conflicts (
    conflict_id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    field TEXT NOT NULL,
    source_a_citation_id TEXT,
    source_b_citation_id TEXT,
    value_a TEXT,
    value_b TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_courses_department ON courses(department_code);
CREATE INDEX IF NOT EXISTS idx_search_documents_course ON search_documents(course_id);
CREATE INDEX IF NOT EXISTS idx_citations_course ON citations(course_id);
"""


def open_db(path: str | Path) -> sqlite3.Connection:
    """Open a SQLite database, creating parent directories as needed."""

    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables, FTS5 virtual table, and triggers."""

    conn.executescript(SCHEMA)
    conn.commit()


def init_db(path: str | Path) -> sqlite3.Connection:
    """Open and initialize a database in one call."""

    conn = open_db(path)
    init_schema(conn)
    return conn


def create_snapshot(conn: sqlite3.Connection, snapshot_id: str, source_ids: list[str], status: str = "fetching") -> None:
    """Create a snapshot record with the given initial status."""

    import json as _json
    from datetime import datetime, timezone

    conn.execute(
        """
        INSERT INTO snapshots (snapshot_id, created_at, refresh_mode, source_ids, status)
        VALUES (?, ?, 'manual', ?, ?)
        ON CONFLICT(snapshot_id) DO UPDATE SET status=excluded.status, source_ids=excluded.source_ids
        """,
        (snapshot_id, datetime.now(timezone.utc).isoformat(), _json.dumps(source_ids), status),
    )
    conn.commit()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}
