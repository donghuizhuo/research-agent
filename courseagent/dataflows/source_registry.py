"""Source registry loading and URL allowlist checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SourceRegistryEntry:
    id: str
    name: str
    tier: int
    type: str
    authority: str
    department: str | None
    url: str | None
    allowed_url_patterns: tuple[str, ...]
    extraction_policy: str
    promotion_rule: str | None
    freshness: dict[str, Any] = field(default_factory=dict)


class SourceRegistry:
    def __init__(self, entries: list[SourceRegistryEntry]) -> None:
        self._entries = {entry.id: entry for entry in entries}

    def get(self, source_id: str) -> SourceRegistryEntry:
        if source_id not in self._entries:
            raise KeyError(f"Unknown source id: {source_id}")
        return self._entries[source_id]

    def all(self) -> list[SourceRegistryEntry]:
        return list(self._entries.values())

    def by_department(self, department: str) -> list[SourceRegistryEntry]:
        return [e for e in self._entries.values() if e.department == department]

    def tier1(self) -> list[SourceRegistryEntry]:
        return [e for e in self._entries.values() if e.tier == 1]


def _entry_from_dict(data: dict[str, Any]) -> SourceRegistryEntry:
    freshness = data.get("freshness", {})
    if not isinstance(freshness, dict):
        freshness = {}
    return SourceRegistryEntry(
        id=data["id"],
        name=data["name"],
        tier=int(data["tier"]),
        type=data["type"],
        authority=data.get("authority", "official"),
        department=data.get("department"),
        url=data.get("url"),
        allowed_url_patterns=tuple(data.get("allowed_url_patterns", [])),
        extraction_policy=data.get("extraction_policy", "supporting_context_by_default"),
        promotion_rule=data.get("promotion_rule"),
        freshness=freshness,
    )


def load_source_registry(path: str | Path) -> SourceRegistry:
    """Parse config/sources.yml into a SourceRegistry."""

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not raw or "sources" not in raw:
        raise ValueError(f"Source registry at {path} must contain a 'sources' key")
    entries = [_entry_from_dict(item) for item in raw["sources"]]
    return SourceRegistry(entries)


def is_url_approved(url: str, registry: SourceRegistry) -> bool:
    """Return True if the URL matches an allowlisted pattern in the registry."""

    if not url:
        return False
    for entry in registry.all():
        for pattern in entry.allowed_url_patterns:
            if fnmatch(url, pattern):
                return True
    return False


def approved_entry_for_url(url: str, registry: SourceRegistry) -> SourceRegistryEntry | None:
    """Return the first registry entry whose allowlist matches the URL, if any."""

    for entry in registry.all():
        for pattern in entry.allowed_url_patterns:
            if fnmatch(url, pattern):
                return entry
    return None


def register_source(conn, entry: SourceRegistryEntry) -> None:
    """Upsert a source registry entry into the sources table."""

    conn.execute(
        """
        INSERT INTO sources (id, name, tier, type, authority, department, url, extraction_policy, promotion_rule)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            tier=excluded.tier,
            type=excluded.type,
            authority=excluded.authority,
            department=excluded.department,
            url=excluded.url,
            extraction_policy=excluded.extraction_policy,
            promotion_rule=excluded.promotion_rule
        """,
        (
            entry.id,
            entry.name,
            entry.tier,
            entry.type,
            entry.authority,
            entry.department,
            entry.url,
            entry.extraction_policy,
            entry.promotion_rule,
        ),
    )
    conn.commit()
