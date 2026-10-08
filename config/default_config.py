"""Default runtime configuration for the UW Course Research Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
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
    llm_mode: LLMMode = field(default_factory=lambda: os.environ.get("COURSEAGENT_LLM_MODE", "deterministic"))
    llm_timeout_seconds: float = 10.0
    max_tool_rounds: int = 4

    def __post_init__(self) -> None:
        if self.llm_mode not in ("deterministic", "model"):
            raise ValueError("llm_mode must be deterministic or model")
        if not math.isfinite(self.llm_timeout_seconds) or not 0 < self.llm_timeout_seconds <= 60:
            raise ValueError("llm_timeout_seconds must be finite and in (0, 60]")


DEFAULT_CONFIG = DefaultConfig()
