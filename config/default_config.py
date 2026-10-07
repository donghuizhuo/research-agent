"""Default runtime configuration for the UW Course Research Agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DefaultConfig:
    data_dir: Path = Path("data")
    snapshots_dir: Path = Path("data/snapshots")
    db_path: Path = Path("data/courseagent.sqlite3")
    sources_path: Path = Path("config/sources.yml")
    llm_provider: str = "deepseek"
    quick_model: str = "deepseek-chat"
    deep_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    max_tool_rounds: int = 4


DEFAULT_CONFIG = DefaultConfig()
