"""Indexing normalized courses, search documents, and citations into SQLite."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Iterable

from courseagent.dataflows.normalizer import NormalizedCourse
from courseagent.dataflows.snapshot_store import utc_now


def _json(value: Any) -> str:
    return json.dumps(value or {}, sort_keys=True)


def upsert_course(conn: sqlite3.Connection, course: NormalizedCourse) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO courses (
            course_id, campus, department_code, course_number, title, description,
            credits, prerequisites, corequisites, source_field_provenance,
            freshness_metadata, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(course_id) DO UPDATE SET
            title=excluded.title,
            description=excluded.description,
            credits=excluded.credits,
            prerequisites=excluded.prerequisites,
            corequisites=excluded.corequisites,
            source_field_provenance=excluded.source_field_provenance,
            freshness_metadata=excluded.freshness_metadata,
            updated_at=excluded.updated_at
        """,
        (
            course.course_id,
            course.campus,
            course.department_code,
            course.course_number,
            course.title,
            course.description,
            course.credits,
            course.prerequisites,
            course.corequisites,
            _json(course.source_field_provenance),
            _json(course.freshness_metadata),
            now,
            now,
        ),
    )


def upsert_search_document(
    conn: sqlite3.Connection,
    *,
    source_document_id: str,
    course_id: str | None,
    department_code: str | None,
    document_type: str,
    title: str,
    body: str,
    freshness_metadata: dict[str, Any] | None = None,
) -> str:
    search_document_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO search_documents (
            search_document_id, source_document_id, course_id, department_code,
            document_type, title, body, freshness_metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            search_document_id,
            source_document_id,
            course_id,
            department_code,
            document_type,
            title,
            body,
            _json(freshness_metadata),
        ),
    )
    return search_document_id


def _citation_from_field(
    course: NormalizedCourse,
    field_name: str,
    source_title: str,
    url: str,
    snapshot_id: str,
    retrieved_at: str | None,
    source_document_id: str,
    evidence_text: str | None,
) -> dict[str, Any] | None:
    if not evidence_text:
        return None
    return {
        "citation_id": uuid.uuid4().hex,
        "source_document_id": source_document_id,
        "course_id": course.course_id,
        "claim_field": field_name,
        "evidence_text": evidence_text,
        "url": url,
        "source_title": source_title,
        "snapshot_id": snapshot_id,
        "retrieved_at": retrieved_at,
        "indexed_at": utc_now(),
    }


def index_courses(
    conn: sqlite3.Connection,
    courses: Iterable[NormalizedCourse],
    *,
    snapshot_id: str,
    source_id: str,
    source_title: str,
    url: str,
    source_document_id: str,
    retrieved_at: str | None = None,
) -> list[dict[str, Any]]:
    """Upsert normalized courses and their search documents/citations.

    Returns the list of citation dicts written so callers can persist or
    surface them. Each substantive field with a value becomes a citation row.
    """

    citations: list[dict[str, Any]] = []
    conn.execute(
        """
        INSERT INTO source_documents (
            source_document_id, source_id, snapshot_id, url, content_type,
            retrieved_at, indexed_at, parse_status
        ) VALUES (?, ?, ?, ?, 'text/html', ?, ?, 'parsed')
        ON CONFLICT(source_document_id) DO NOTHING
        """,
        (source_document_id, source_id, snapshot_id, url, retrieved_at, utc_now()),
    )
    for course in courses:
        upsert_course(conn, course)
        title = course.title or ""
        description = course.description or ""
        body = " ".join(
            part
            for part in [
                course.course_id,
                title,
                description,
                course.prerequisites or "",
                course.corequisites or "",
            ]
            if part
        )
        upsert_search_document(
            conn,
            source_document_id=source_document_id,
            course_id=course.course_id,
            department_code=course.department_code,
            document_type="course_record",
            title=f"{course.course_id}: {title}".strip(),
            body=body,
            freshness_metadata={"snapshot_id": snapshot_id, "source_id": source_id},
        )
        field_values = {
            "title": course.title,
            "description": course.description,
            "credits": course.credits,
            "prerequisites": course.prerequisites,
            "corequisites": course.corequisites,
        }
        for field_name, value in field_values.items():
            citation = _citation_from_field(
                course,
                field_name,
                source_title,
                url,
                snapshot_id,
                retrieved_at,
                source_document_id,
                value,
            )
            if citation:
                conn.execute(
                    """
                    INSERT INTO citations (
                        citation_id, source_document_id, course_id, claim_field,
                        evidence_text, url, source_title, snapshot_id, retrieved_at, indexed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        citation["citation_id"],
                        citation["source_document_id"],
                        citation["course_id"],
                        citation["claim_field"],
                        citation["evidence_text"],
                        citation["url"],
                        citation["source_title"],
                        citation["snapshot_id"],
                        citation["retrieved_at"],
                        citation["indexed_at"],
                    ),
                )
                citations.append(citation)
    conn.commit()
    return citations
