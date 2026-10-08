"""CourseResearchGraph orchestration class."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from langgraph.types import Overwrite

from config.default_config import DefaultConfig
from courseagent.agents.grounding import redact_sensitive_input
from courseagent.agents.schemas import CourseAnswer
from courseagent.graph.checkpointer import CheckpointerManager, thread_id_for
from courseagent.graph.setup import setup_graph


class CourseResearchGraph:
    """Compiles and runs the course research graph with checkpoint persistence."""

    def __init__(
        self,
        config: DefaultConfig | None = None,
        conn: sqlite3.Connection | None = None,
        quick_llm: Any | None = None,
        deep_llm: Any | None = None,
    ) -> None:
        self.config = config or DefaultConfig()
        self.conn = conn
        self.quick_llm = quick_llm
        self.deep_llm = deep_llm
        self._checkpoint_manager: CheckpointerManager | None = None
        self._app: Any | None = None

    def _ensure_conn(self) -> sqlite3.Connection:
        if self.conn is None:
            from courseagent.dataflows.db import init_db

            self.conn = init_db(self.config.db_path)
        return self.conn

    def compile(self) -> Any:
        """Compile (or return the cached) graph with a persistent checkpointer.

        The compiled app and its CheckpointerManager are reused across `run()`
        calls to avoid leaking a SQLite connection per invocation.
        """

        if self._app is not None:
            return self._app
        conn = self._ensure_conn()
        graph = setup_graph(conn, quick_llm=self.quick_llm, deep_llm=self.deep_llm)
        self._checkpoint_manager = CheckpointerManager(self.config.data_dir)
        self._app = graph.compile(checkpointer=self._checkpoint_manager.saver)
        return self._app

    def close(self) -> None:
        """Release the checkpointer connection and reset the compiled app."""

        if self._checkpoint_manager is not None:
            self._checkpoint_manager.close()
            self._checkpoint_manager = None
        self._app = None

    def run(self, query: str, workflow_id: str | None = None) -> dict[str, Any]:
        """Run the graph once for a query and return a serializable result."""

        query = redact_sensitive_input(query)
        workflow_id = workflow_id or uuid.uuid4().hex
        app = self.compile()
        config = {"configurable": {"thread_id": thread_id_for(workflow_id)}}
        # Keep the workflow/checkpoint history, but each query owns its retrieval
        # and answer state. Empty lists alone would append through the reducers.
        initial = {
            "query": query,
            "workflow_id": workflow_id,
            **{key: Overwrite([]) for key in (
                "retrieved_courses", "citations", "freshness", "limitations", "conflicts",
            )},
            "interpreted_filters": Overwrite({}),
            "intent": None,
            "answer": None,
            "structured_answer": None,
            "needs_clarification": False,
            "status": "active",
        }
        state: dict[str, Any] = app.invoke(initial, config=config)

        structured = state.get("structured_answer")
        if structured is not None and not isinstance(structured, dict):
            structured = structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)
        else:
            structured = None

        answer = state.get("answer")
        citations = state.get("citations", [])
        return {
            "workflow_id": workflow_id,
            "query": query,
            "answer": answer,
            "structured_answer": structured,
            "citations": _serialize(citations),
            "freshness": _serialize(state.get("freshness", [])),
            "limitations": list(state.get("limitations", [])),
            "conflicts": list(state.get("conflicts", [])),
            "needs_clarification": bool(state.get("needs_clarification", False)),
            "status": state.get("status", "ok"),
        }


def _serialize(items: list[Any]) -> list[Any]:
    out: list[Any] = []
    for item in items or []:
        if hasattr(item, "model_dump"):
            out.append(item.model_dump())
        elif isinstance(item, dict):
            out.append(item)
        else:
            out.append(json.loads(json.dumps(item, default=str)))
    return out
