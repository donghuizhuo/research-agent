"""Approved-source fetching with registry allowlist enforcement."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

import httpx

from courseagent.dataflows.snapshot_store import SnapshotStore, StoredSnapshot
from courseagent.dataflows.source_registry import SourceRegistry, is_url_approved


@dataclass(frozen=True)
class FetchResult:
    source_id: str
    url: str
    status_code: int
    stored: StoredSnapshot | None
    error: str | None


def fetch_approved_sources(
    registry: SourceRegistry,
    snapshot_store: SnapshotStore,
    snapshot_id: str,
    source_ids: Iterable[str] | None = None,
    client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> list[FetchResult]:
    """Fetch only allowlisted source URLs and persist raw snapshots.

    If source_ids is None, fetch every registry entry that has a URL.
    """

    entries = registry.all() if source_ids is None else [registry.get(sid) for sid in source_ids]
    results: list[FetchResult] = []
    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        for entry in entries:
            if not entry.url:
                continue
            if not is_url_approved(entry.url, registry):
                results.append(
                    FetchResult(
                        source_id=entry.id,
                        url=entry.url,
                        status_code=0,
                        stored=None,
                        error="URL not approved by registry allowlist",
                    )
                )
                continue
            try:
                response = client.get(entry.url)
                stored = snapshot_store.write(snapshot_id, entry.id, response.content)
                results.append(
                    FetchResult(
                        source_id=entry.id,
                        url=entry.url,
                        status_code=response.status_code,
                        stored=stored,
                        error=None if response.status_code < 400 else f"HTTP {response.status_code}",
                    )
                )
            except Exception as exc:  # noqa: BLE001 - capture and continue per-source
                results.append(
                    FetchResult(
                        source_id=entry.id,
                        url=entry.url,
                        status_code=0,
                        stored=None,
                        error=str(exc),
                    )
                )
            time.sleep(0.2)  # polite crawl spacing
        return results
    finally:
        if owns_client:
            client.close()
