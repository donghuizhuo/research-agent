"""SqliteSaver checkpointer wrapper and deterministic thread_id helpers."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


def thread_id_for(workflow_id: str) -> str:
    """Derive a stable LangGraph thread_id from a workflow_id."""

    return hashlib.sha256(workflow_id.encode("utf-8")).hexdigest()[:32]


class CheckpointerManager:
    """Owns a persistent SQLite connection and its SqliteSaver instance.

    The connection must remain open for the lifetime of the compiled graph,
    so this class keeps both alive and exposes the saver.
    """

    def __init__(self, data_dir: str | Path) -> None:
        data_path = Path(data_dir)
        data_path.mkdir(parents=True, exist_ok=True)
        db_path = data_path / "checkpoints.sqlite3"
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.saver = SqliteSaver(self.conn)

    def close(self) -> None:
        self.conn.close()


def get_checkpointer(data_dir: str | Path) -> SqliteSaver:
    """Create and return a ready-to-use SqliteSaver.

    NOTE: the returned saver owns a SQLite connection that must stay open for
    the lifetime of the compiled graph. Prefer `CheckpointerManager` for
    long-lived use; this helper is kept for direct single-use callers.
    """

    manager = CheckpointerManager(data_dir)
    return manager.saver
