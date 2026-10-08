"""FastAPI application factory with routing and static web UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.default_config import DefaultConfig


def create_app(config: DefaultConfig | None = None) -> FastAPI:
    app = FastAPI(title="UW Course Research Agent API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    cfg = config or DefaultConfig()
    app.state.config = cfg

    from courseagent.api.routes import admin, courses, search, workflows

    search.register(app)
    courses.register(app)
    workflows.register(app)
    admin.register(app)

    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    return app


def get_graph(app: FastAPI) -> Any:
    """Return a CourseResearchGraph for the app's configuration."""

    from courseagent.graph.runtime import create_graph

    cfg = app.state.config
    return create_graph(cfg)
