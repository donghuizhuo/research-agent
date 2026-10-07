"""Department page chunking for searchable supporting context (Tier 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup


@dataclass
class DepartmentChunk:
    title: str
    body: str
    department_code: str
    source_ref: str
    metadata: dict[str, Any] = field(default_factory=dict)


def chunk_department_page(
    html: str,
    department_code: str,
    source_doc: dict[str, Any] | None = None,
    max_chunk_chars: int = 2000,
) -> list[DepartmentChunk]:
    """Chunk a department page into searchable context chunks.

    These chunks are supporting context only and are never promoted to
    normalized course facts. Each chunk carries its source reference.
    """

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    source_ref = (source_doc or {}).get("source_document_id", "department")

    title = _clean(soup.title.get_text(" ", strip=True)) if soup.title else department_code
    body_text = _clean(soup.get_text(" ", strip=True))
    chunks: list[DepartmentChunk] = []
    for start in range(0, len(body_text), max_chunk_chars):
        piece = body_text[start : start + max_chunk_chars]
        if not piece.strip():
            continue
        chunks.append(
            DepartmentChunk(
                title=title,
                body=piece,
                department_code=department_code,
                source_ref=source_ref,
            )
        )
    if not chunks:
        chunks.append(DepartmentChunk(title=title, body="", department_code=department_code, source_ref=source_ref))
    return chunks


def _clean(value: str) -> str:
    import re

    return re.sub(r"\s+", " ", value).strip()
