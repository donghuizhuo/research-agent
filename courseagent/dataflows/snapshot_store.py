"""Raw snapshot persistence for approved source content."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(content: bytes | str) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class StoredSnapshot:
    snapshot_id: str
    source_id: str
    path: str
    content_hash: str
    retrieved_at: str


class SnapshotStore:
    """Writes raw source content to data/snapshots/{snapshot_id}/{source_id}.html."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)

    def _snapshot_dir(self, snapshot_id: str) -> Path:
        return self.base_dir / snapshot_id

    def write(self, snapshot_id: str, source_id: str, content: bytes | str) -> StoredSnapshot:
        snapshot_dir = self._snapshot_dir(snapshot_id)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            content = content.encode("utf-8")
        path = snapshot_dir / f"{source_id}.html"
        path.write_bytes(content)
        return StoredSnapshot(
            snapshot_id=snapshot_id,
            source_id=source_id,
            path=str(path),
            content_hash=content_hash(content),
            retrieved_at=utc_now(),
        )

    def read(self, snapshot_id: str, source_id: str) -> bytes:
        path = self._snapshot_dir(snapshot_id) / f"{source_id}.html"
        if not path.exists():
            raise FileNotFoundError(f"Snapshot file not found: {path}")
        return path.read_bytes()
