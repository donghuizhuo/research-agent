"""POST /admin/snapshots/import route."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from courseagent.api.schemas import SnapshotImportResponse

router = APIRouter()


class ImportRequest(BaseModel):
    source_ids: list[str] | None = None


@router.post("/admin/snapshots/import", response_model=SnapshotImportResponse)
def import_snapshot(request: Request, payload: ImportRequest | None = None) -> SnapshotImportResponse:
    from courseagent.dataflows.source_registry import load_source_registry

    cfg = request.app.state.config
    registry = load_source_registry(cfg.sources_path)
    requested = (payload.source_ids if payload else None) or []
    if requested:
        unknown = [sid for sid in requested if sid not in {e.id for e in registry.all()}]
        if unknown:
            return SnapshotImportResponse(status="failed", message=f"Unknown source IDs: {unknown}")

    # Delegate to the ingest CLI command path (runs synchronously for MVP).
    from courseagent.cli import main as cli

    cli.ingest(source_ids=requested or None)
    return SnapshotImportResponse(status="completed", imported_source_ids=requested)


def register(app) -> None:
    app.include_router(router)
