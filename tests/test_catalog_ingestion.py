"""Exercise normal approved fetching -> parser -> index -> API without seeding courses."""
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from config.default_config import DefaultConfig
from courseagent.cli import main
from courseagent.api.app import create_app
from courseagent.dataflows import fetcher
from courseagent.dataflows.db import open_db
from courseagent.dataflows.source_registry import load_source_registry


def test_approved_catalog_ingestion_search_and_detail(tmp_path, monkeypatch):
    cfg = DefaultConfig(
        data_dir=tmp_path, snapshots_dir=tmp_path / "snapshots",
        db_path=tmp_path / "courses.sqlite3", sources_path=Path("config/sources.yml"),
    )
    registry = load_source_registry(cfg.sources_path)
    monkeypatch.setattr(main, "_load_registry", lambda: (registry, cfg))
    urls = {
        registry.get(f"uw_{dept}_catalog").url:
            (Path(__file__).parent / "fixtures" / f"uw_{dept}_catalog.html").read_bytes()
        for dept in ("cse", "info")
    }
    requested = []

    def respond(request):
        requested.append(str(request.url))
        return httpx.Response(200, content=urls[str(request.url)])

    original_fetch = fetcher.fetch_approved_sources
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(fetcher, "fetch_approved_sources", lambda *a, **kw:
                            original_fetch(*a, **kw, client=client))
        result = CliRunner().invoke(main.app, ["ingest", "uw_cse_catalog", "uw_info_catalog"])
    assert result.exit_code == 0, result.output
    assert "Indexed 11 courses total." in result.output
    assert set(requested) == set(urls)
    conn = open_db(cfg.db_path)
    snapshot = dict(conn.execute("SELECT * FROM snapshots").fetchone())
    assert snapshot["status"] == "indexed"
    assert set(json.loads(snapshot["source_ids"])) == {"uw_cse_catalog", "uw_info_catalog"}
    assert conn.execute("SELECT count(*) FROM courses").fetchone()[0] == 11
    assert conn.execute("SELECT count(*) FROM search_documents_fts").fetchone()[0] == 11
    course = dict(conn.execute("SELECT * FROM courses WHERE course_id='CSE-142'").fetchone())
    doc = dict(conn.execute("SELECT * FROM source_documents WHERE source_id='uw_cse_catalog'").fetchone())
    assert course["campus"] == "seattle"
    assert json.loads(course["source_field_provenance"])["title"] == doc["source_document_id"]
    assert json.loads(course["freshness_metadata"])["snapshot_id"] == snapshot["snapshot_id"]
    conn.close()

    with TestClient(create_app(cfg)) as api:
        for query, expected in [("CSE 142", {"CSE-142"}), ("INFO", {"INFO-180", "INFO-198", "INFO-200", "INFO-201", "INFO-340"})]:
            response = api.post("/course-search", json={"query": query})
            assert response.status_code == 200
            rows = response.json()["results"]
            assert {r["course_id"] for r in rows} == expected
            for row in rows:
                assert row["citations"]
                assert all(c["url"] in urls and c["snapshot_id"] == snapshot["snapshot_id"] and c["retrieved_at"] for c in row["citations"])
        discovery = api.post("/course-search", json={"query": "machine learning"}).json()
        assert "INFO-180" in {r["course_id"] for r in discovery["results"]}
        detail = api.get("/courses/CSE-143").json()
        assert detail["prerequisites"] == "CSE 142."
        assert detail["title"] == "Computer Programming II"
        assert any(c["evidence_text"] == "CSE 142." for c in detail["citations"])
        assert api.post("/course-search", json={"query": "CSE 999"}).json()["results"] == []

        # The screenshot request must use exact lookup on the normally ingested
        # catalog, with identical facts/provenance in fresh and reused sessions.
        bare = api.post("/course-search", json={"query": "CSE 143"}).json()
        workflow_id = discovery["workflow_id"]
        for query in [
            "show me information about the cse 143",
            "Tell me about (CsE 143)!", "What is CSE 143?", "CSE\t 143",
        ]:
            for session in [None, workflow_id]:
                payload = {"query": query}
                if session:
                    payload["workflow_id"] = session
                response = api.post("/course-search", json=payload)
                assert response.status_code == 200
                exact = response.json()
                assert exact["answer_type"] == "direct_answer"
                assert exact["results"] == bare["results"]
                assert exact["results"][0]["course_id"] == "CSE-143"
                assert exact["results"][0]["citations"]
                assert all(c["snapshot_id"] == snapshot["snapshot_id"] for c in exact["results"][0]["citations"])
                state = api.get(exact["state_ref"]).json()
                assert state["active_query"] == query
                assert state["selected_courses"] == ["CSE-143"]
                if session:
                    assert exact["workflow_id"] == session

        missing = api.post("/course-search", json={
            "query": "show me information about the cse 999",
            "workflow_id": workflow_id,
        }).json()
        assert missing["answer_type"] == "no_results"
        assert missing["results"] == []
        assert any("CSE-999" in note for note in missing["limitations"])
        assert api.get(missing["state_ref"]).json()["selected_courses"] == []
        for query in ["machine learning", "CSE courses"]:
            fresh = api.post("/course-search", json={"query": query}).json()
            reused = api.post("/course-search", json={"query": query, "workflow_id": workflow_id}).json()
            assert reused["answer_type"] == fresh["answer_type"]
            assert fresh["results"]
            assert reused["results"] == fresh["results"]
