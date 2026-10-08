"""Controlled synthesis must preserve retrieved catalog facts and provenance."""

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from config.default_config import DefaultConfig
from courseagent.agents.answer_composer import compose_answer
from courseagent.agents.schemas import Citation, CourseSearchResult, FreshnessMetadata
from courseagent.api import app as api_app
from courseagent.cli import main
from courseagent.dataflows import fetcher
from courseagent.dataflows.source_registry import load_source_registry
from courseagent.graph.course_graph import CourseResearchGraph


class ControlledModel:
    def __init__(self, content="CSE 142 has 999 credits", error=None):
        self.content = content
        self.error = error
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.content)


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    cfg = DefaultConfig(data_dir=tmp_path, snapshots_dir=tmp_path / "snapshots",
                        db_path=tmp_path / "courses.sqlite3", llm_mode="deterministic")
    registry = load_source_registry(cfg.sources_path)
    monkeypatch.setattr(main, "_load_registry", lambda: (registry, cfg))
    urls = {registry.get(f"uw_{dept}_catalog").url:
            (Path(__file__).parent / "fixtures" / f"uw_{dept}_catalog.html").read_bytes()
            for dept in ("cse", "info")}
    original = fetcher.fetch_approved_sources
    with httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=urls[str(request.url)]))) as client:
        monkeypatch.setattr(fetcher, "fetch_approved_sources",
                            lambda *a, **kw: original(*a, **kw, client=client))
        result = CliRunner().invoke(main.app, ["ingest", "uw_cse_catalog", "uw_info_catalog"])
    assert result.exit_code == 0, result.output
    assert "Indexed 11 courses total." in result.output
    return cfg


@pytest.mark.parametrize("count", [0, 1, 3])
@pytest.mark.parametrize("as_dict", [False, True])
@pytest.mark.parametrize("content,error", [
    ("CSE 142 has 999 credits", None), ("CSE 142 has 4 credits", None), ("", None), ("  ", None),
    (None, None), ([], None), ("unused", RuntimeError("provider failed")),
])
def test_composer_preserves_every_typed_field(count, as_dict, content, error):
    courses = [CourseSearchResult(
        course_id=f"CSE-{142 + i}", department_code="CSE", course_number=str(142 + i),
        title="Catalog title", description="Catalog description", credits="4",
        prerequisites="MATH 124", corequisites="Lab", score=0.75,
        citations=[Citation(citation_id=f"cite-{i}", course_id=f"CSE-{142 + i}",
                            source_document_id="doc", claim_field="credits", evidence_text="4",
                            url="https://example.test/catalog", source_title="Catalog",
                            snapshot_id="snapshot", retrieved_at="retrieved", indexed_at="indexed")],
        freshness=[FreshnessMetadata(snapshot_id="snapshot", source_id="source",
                                     retrieved_at="retrieved", indexed_at="indexed")],
    ) for i in range(count)]
    state = {"query": "CSE", "workflow_id": "workflow", "retrieved_courses": courses,
             "citations": [c for course in courses for c in course.citations],
             "limitations": ["Existing limitation"], "status": "ok" if count else "not_found"}
    if as_dict:
        state["retrieved_courses"] = [c.model_dump() for c in courses]
        state["citations"] = [c.model_dump() for course in courses for c in course.citations]
    baseline = compose_answer(state)
    model = ControlledModel(content, error)
    result = compose_answer({**state, "deep_llm": model})
    assert result["structured_answer"] == baseline["structured_answer"]
    assert model.calls == (1 if count else 0)
    expected = content if count and isinstance(content, str) and content.strip() and not error else baseline["answer"]
    assert result["answer"] == expected


@pytest.mark.parametrize("content,error", [
    ("CSE 142 has 999 credits", None), ("", None), (None, RuntimeError("provider failed")),
])
def test_api_success_failure_empty_and_workflow_reuse(catalog, monkeypatch, content, error):
    model = ControlledModel(content, error)
    active_model = None
    graphs = []
    observed = []

    def get_graph(app):
        graph = CourseResearchGraph(app.state.config, deep_llm=active_model)
        graphs.append(graph)
        original = graph.run

        def run(*a, **kw):
            result = original(*a, **kw)
            observed.append(result)
            return result

        graph.run = run
        return graph

    try:
        with TestClient(api_app.create_app(catalog)) as client:
            monkeypatch.setattr(api_app, "get_graph", get_graph)
            expected = {q: client.post("/course-search", json={"query": q}).json()
                        for q in ("CSE 142", "CSE", "CSE 999")}
            expected_graphs = {r["query"]: r for r in observed}
            active_model = model
            workflow_id = None
            for query in ("CSE 142", "CSE", "CSE 999", "CSE 142"):
                response = client.post("/course-search", json={"query": query, "workflow_id": workflow_id})
                assert response.status_code == 200
                actual = response.json()
                workflow_id = actual["workflow_id"]
                assert actual["results"] == expected[query]["results"]
                assert actual["answer_type"] == expected[query]["answer_type"]
                assert actual["limitations"] == expected[query]["limitations"]
                graph_result = observed[-1]
                assert graph_result["structured_answer"] is not None
                baseline = expected_graphs[query]
                assert graph_result["citations"] == baseline["citations"]
                assert graph_result["freshness"] == baseline["freshness"]
                assert {**graph_result["structured_answer"], "workflow_id": None} == {
                    **baseline["structured_answer"], "workflow_id": None}
                if query == "CSE 999":
                    assert graph_result["citations"] == []
                    assert graph_result["structured_answer"]["course"] is None
                    assert graph_result["structured_answer"]["ranked_courses"] == []
                state = client.get(f"/workflows/{workflow_id}").json()
                assert state["selected_courses"] == [c["course_id"] for c in actual["results"]]
            assert model.calls == 3
    finally:
        for graph in graphs:
            graph.close()
