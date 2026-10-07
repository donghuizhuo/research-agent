"""Typer CLI entry point: ingest, search, serve."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import typer

from courseagent.dataflows.db import create_snapshot, init_db
from courseagent.dataflows.indexer import index_courses
from courseagent.dataflows.parsers.department_page import chunk_department_page
from courseagent.dataflows.parsers.uw_course_catalog import parse_uw_course_catalog
from courseagent.dataflows.snapshot_store import SnapshotStore, utc_now
from courseagent.dataflows.source_registry import load_source_registry, register_source
from courseagent.dataflows import fetcher, normalizer

app = typer.Typer(help="UW Course Research Agent CLI")


def _load_registry() -> tuple:
    from courseagent.dataflows.source_registry import SourceRegistry
    from config.default_config import DEFAULT_CONFIG

    registry = load_source_registry(DEFAULT_CONFIG.sources_path)
    return registry, DEFAULT_CONFIG


@app.command()
def ingest(
    source_ids: list[str] | None = typer.Argument(None, help="Optional subset of approved source IDs"),
) -> None:
    """Fetch, parse, normalize, and index approved UW Seattle course sources."""

    registry, config = _load_registry()
    snapshot_id = uuid.uuid4().hex
    store = SnapshotStore(config.snapshots_dir)
    db = init_db(config.db_path)

    target_ids = list(source_ids) if source_ids else [e.id for e in registry.all() if e.url]
    create_snapshot(db, snapshot_id, target_ids, status="fetching")

    results = fetcher.fetch_approved_sources(registry, store, snapshot_id, source_ids=source_ids)
    typer.echo(f"Snapshot {snapshot_id}")

    total_courses = 0
    for result in results:
        if result.error or result.stored is None:
            typer.echo(f"  [skip] {result.source_id}: {result.error or 'no content'}")
            continue
        entry = registry.get(result.source_id)
        register_source(db, entry)
        content = store.read(snapshot_id, result.source_id).decode("utf-8", errors="replace")
        source_document_id = uuid.uuid4().hex

        if entry.type == "course_catalog" and entry.extraction_policy == "normalized_facts_allowed":
            parsed = parse_uw_course_catalog(content, {"source_document_id": source_document_id})
            courses = normalizer.normalize_courses(parsed, snapshot_id, entry.id)
            index_courses(
                db,
                courses,
                snapshot_id=snapshot_id,
                source_id=entry.id,
                source_title=entry.name,
                url=entry.url or "",
                source_document_id=source_document_id,
                retrieved_at=result.stored.retrieved_at,
            )
            total_courses += len(courses)
            typer.echo(f"  [indexed] {entry.id}: {len(courses)} courses")
        else:
            chunks = chunk_department_page(
                content,
                entry.department or entry.id,
                {"source_document_id": source_document_id},
            )
            typer.echo(f"  [context] {entry.id}: {len(chunks)} department chunks (supporting context)")

    # Persist snapshot record with indexed status.
    db.execute(
        """
        INSERT INTO snapshots (snapshot_id, created_at, refresh_mode, source_ids, status)
        VALUES (?, ?, 'manual', ?, 'indexed')
        ON CONFLICT(snapshot_id) DO UPDATE SET
            source_ids=excluded.source_ids, status=excluded.status
        """,
        (snapshot_id, utc_now(), json.dumps([r.source_id for r in results if r.stored])),
    )
    db.commit()
    typer.echo(f"Indexed {total_courses} courses total.")


@app.command()
def search(query: str = typer.Argument(...)) -> None:
    """Run a search through the full LangGraph workflow."""

    from courseagent.graph.course_graph import CourseResearchGraph

    registry, config = _load_registry()
    graph = CourseResearchGraph(config)
    result = graph.run(query)
    typer.echo(json.dumps(result, indent=2, default=str))


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Serve the FastAPI app and static web UI via uvicorn."""

    import uvicorn

    uvicorn.run("courseagent.api.app:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    app()
