"""Default runtime configuration for the UW Course Research Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Literal

LLMMode = Literal["deterministic", "model"]


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
    llm_mode: LLMMode = field(default_factory=lambda: os.environ.get("COURSEAGENT_LLM_MODE", "model"))
    max_tool_rounds: int = 4

    def __post_init__(self) -> None:
        if self.llm_mode not in ("deterministic", "model"):
            raise ValueError("llm_mode must be deterministic or model")


DEFAULT_CONFIG = DefaultConfig()
