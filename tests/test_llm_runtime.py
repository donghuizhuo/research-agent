"""Offline API/CLI provider mode, credentials, failures and transport bounds."""

from dataclasses import replace
import json
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from config.default_config import DefaultConfig
from courseagent.agents.query_understanding import _heuristic_intent
from courseagent.api import app as api_app
from courseagent.cli import main
from courseagent.graph.runtime import create_graph
from courseagent.llm_clients import factory
from test_llm_contract import ControlledModel, catalog as catalog  # shared approved-ingestion fixture


class QuickModel:
    def __init__(self, error=None, empty=False):
        self.error = error
        self.empty = empty
        self.calls = 0

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        if self.empty:
            return None
        return _heuristic_intent(messages[-1]["content"])


@pytest.mark.parametrize("case", ["default", "missing", "initialization", "success", "failure", "timeout", "empty", "classification_empty"])
def test_api_and_cli_share_opt_in_and_fallback(catalog, monkeypatch, case):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "unrelated-key-must-not-be-used")
    mode = "deterministic" if case == "default" else "model"
    cfg = replace(catalog, llm_mode=mode)
    error = (httpx.ReadTimeout("controlled timeout") if case == "timeout" else
             RuntimeError("controlled failure") if case == "failure" else None)
    quick = QuickModel(error, empty=case == "classification_empty")
    deep = ControlledModel("" if case == "empty" else "CSE 142 has 999 credits", error)
    kwargs_seen = []

    def constructor(**kwargs):
        kwargs_seen.append(kwargs)
        if case == "initialization" and len(kwargs_seen) % 2 == 0:
            raise RuntimeError("deep initialization failed")
        return quick if kwargs["temperature"] else deep

    monkeypatch.setattr(factory, "ChatOpenAI", constructor)
    if case != "missing":
        monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-deepseek-key")
    registry, _ = main._load_registry()
    monkeypatch.setattr(main, "_load_registry", lambda: (registry, cfg))
    runner = CliRunner()
    baseline = runner.invoke(main.app, ["search", "CSE 142", "--llm-mode", "deterministic"])
    assert baseline.exit_code == 0, baseline.output
    expected = json.loads(baseline.output)
    result = runner.invoke(main.app, ["search", "CSE 142"])
    assert result.exit_code == 0, result.output
    actual = json.loads(result.output)
    for field in ("course", "ranked_courses", "citations", "freshness", "limitations", "status"):
        assert actual["structured_answer"][field] == expected["structured_answer"][field]
    assert actual["citations"] == expected["citations"]
    assert actual["freshness"] == expected["freshness"]
    assert actual["answer"] == (deep.content if case in ("success", "classification_empty") else expected["answer"])

    with TestClient(api_app.create_app(replace(cfg, llm_mode="deterministic"))) as client:
        baseline_api = client.post("/course-search", json={"query": "CSE 142"}).json()
    with TestClient(api_app.create_app(cfg)) as client:
        response = client.post("/course-search", json={"query": "CSE 142"})
        assert response.status_code == 200
        actual_api = response.json()
    assert actual_api["answer_type"] == "direct_answer"
    assert actual_api["results"] == baseline_api["results"]
    assert actual_api["limitations"] == baseline_api["limitations"]
    enabled = case not in ("default", "missing", "initialization")
    assert quick.calls == 0
    assert deep.calls == (2 if enabled else 0)
    assert len(kwargs_seen) == (0 if case in ("default", "missing") else 4)
    for kwargs in kwargs_seen:
        assert kwargs["api_key"] == "synthetic-deepseek-key"
        assert kwargs["base_url"] == cfg.deepseek_base_url
        assert kwargs["model"] == cfg.deep_model
        assert kwargs["timeout"] == 10.0
        assert kwargs["max_retries"] == 0


def test_model_flag_overrides_deterministic_configuration(catalog, monkeypatch):
    quick, deep = QuickModel(), ControlledModel()
    called = Mock(side_effect=[quick, deep])
    monkeypatch.setattr(factory, "create_tier_client", called)
    result = CliRunner().invoke(main.app, ["search", "CSE 142", "--llm-mode", "model"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["answer"] == deep.content
    assert called.call_count == 2
    assert quick.calls == 0
    assert deep.calls == 1


def test_environment_opt_in_and_explicit_deterministic_override(monkeypatch):
    monkeypatch.delenv("COURSEAGENT_LLM_MODE", raising=False)
    assert DefaultConfig().llm_mode == "deterministic"
    monkeypatch.setenv("COURSEAGENT_LLM_MODE", "model")
    assert api_app.create_app().state.config.llm_mode == "model"
    assert api_app.create_app(DefaultConfig(llm_mode="deterministic")).state.config.llm_mode == "deterministic"
    monkeypatch.setattr(factory, "create_tier_client", Mock(side_effect=AssertionError("unexpected provider")))
    graph = create_graph(DefaultConfig(llm_mode="model", llm_provider="unsupported"))
    assert graph.quick_llm is graph.deep_llm is None
    factory.create_tier_client.assert_not_called()


def test_classification_binding_failure_falls_back(catalog, monkeypatch):
    quick = Mock()
    quick.with_structured_output.side_effect = RuntimeError("binding failed")
    deep = ControlledModel()
    monkeypatch.setattr(factory, "create_tier_client", Mock(side_effect=[quick, deep]))
    result = CliRunner().invoke(main.app, ["search", "CSE courses", "--llm-mode", "model"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["structured_answer"]["ranked_courses"]
    quick.with_structured_output.assert_called_once()
    assert deep.calls == 1


def test_serve_passes_mode_to_real_app_configuration(monkeypatch):
    run = Mock()
    monkeypatch.setattr("uvicorn.run", run)
    monkeypatch.setenv("COURSEAGENT_LLM_MODE", "model")
    result = CliRunner().invoke(main.app, ["serve", "--llm-mode", "deterministic", "--port", "8123"])
    assert result.exit_code == 0, result.output
    assert run.call_args.args[0].state.config.llm_mode == "deterministic"
    assert run.call_args.kwargs == {"host": "127.0.0.1", "port": 8123}


def test_factory_explicit_credential_overrides_environment(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-key")
    constructor = Mock()
    monkeypatch.setattr(factory, "ChatOpenAI", constructor)
    factory.create_tier_client(DefaultConfig(), "deep", api_key="explicit-key")
    assert constructor.call_args.kwargs["api_key"] == "explicit-key"


def test_factory_selects_each_configured_tier(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-key")
    constructor = Mock()
    monkeypatch.setattr(factory, "ChatOpenAI", constructor)
    cfg = DefaultConfig(quick_model="configured-quick", deep_model="configured-deep")
    factory.create_tier_client(cfg, "quick")
    factory.create_tier_client(cfg, "deep")
    assert [call.kwargs["model"] for call in constructor.call_args_list] == [
        "configured-quick", "configured-deep"]


def test_invalid_runtime_mode_rejected(monkeypatch):
    monkeypatch.setenv("COURSEAGENT_LLM_MODE", "typo")
    with pytest.raises(ValueError, match="llm_mode"):
        DefaultConfig()


def test_real_client_timeout_has_no_retry_and_deterministic_fallback(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-key")
    requests = []

    def timeout(request):
        requests.append(request)
        raise httpx.ReadTimeout("synthetic transport timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout)) as transport:
        llm = factory.create_tier_client(DefaultConfig(), "deep", http_client=transport)
        from courseagent.agents.answer_composer import compose_answer
        from courseagent.agents.schemas import CourseSearchResult

        state = {"query": "CSE 142", "retrieved_courses": [CourseSearchResult(
            course_id="CSE-142", department_code="CSE", course_number="142", credits="4")],
            "deep_llm": llm}
        actual = compose_answer(state)
        assert actual["structured_answer"].course.credits == "4"
        assert "Credits: 4" in actual["answer"]
    assert len(requests) == 1
    assert requests[0].extensions["timeout"] == {
        "connect": 10.0, "read": 10.0, "write": 10.0, "pool": 10.0}
    assert requests[0].headers["authorization"] == "Bearer synthetic-key"


@pytest.mark.parametrize("private", [
    "My student id is 1234567; explain CSE 142",
    "email user@uw.edu; explain CSE 142",
    "my netid: jsmith42; explain CSE 142",
])
def test_api_cli_redact_before_models_and_checkpoints(catalog, monkeypatch, private):
    from courseagent.agents.grounding import redact_sensitive_input
    from courseagent.graph.checkpointer import CheckpointerManager

    prompts = {"quick": [], "deep": []}

    class CapturingQuick(QuickModel):
        def invoke(self, messages):
            prompts["quick"].append(messages)
            self.calls += 1
            return _heuristic_intent("CSE 142")

    class CapturingDeep(ControlledModel):
        def invoke(self, messages):
            prompts["deep"].append(messages)
            return super().invoke(messages)

    quick, deep = CapturingQuick(), CapturingDeep()
    monkeypatch.setattr(factory, "create_tier_client",
                        lambda config, tier: quick if tier == "quick" else deep)
    registry, _ = main._load_registry()
    cfg = replace(catalog, llm_mode="model")
    monkeypatch.setattr(main, "_load_registry", lambda: (registry, cfg))
    runner = CliRunner()
    baseline = json.loads(runner.invoke(main.app, ["search", "CSE 142"]).output)
    result = runner.invoke(main.app, ["search", private])
    assert result.exit_code == 0, result.output
    actual = json.loads(result.output)
    assert actual["query"] == redact_sensitive_input(private)
    for field in ("course", "ranked_courses", "citations", "freshness", "limitations", "status"):
        assert actual["structured_answer"][field] == baseline["structured_answer"][field]
    with TestClient(api_app.create_app(cfg)) as client:
        expected = client.post("/course-search", json={"query": "CSE 142"}).json()
        response = client.post("/course-search", json={"query": private})
        assert response.status_code == 200
        assert response.json()["results"] == expected["results"]
        assert response.json()["answer_type"] == expected["answer_type"]
    assert quick.calls == 2
    assert deep.calls == 4
    manager = CheckpointerManager(catalog.data_dir)
    try:
        checkpoints = [entry.checkpoint for entry in manager.saver.list(None)]
    finally:
        manager.close()
    assert checkpoints
    assert any(entry["channel_values"].get("query") == redact_sensitive_input(private)
               for entry in checkpoints)
    for emitted in (prompts["quick"], prompts["deep"], checkpoints, actual):
        serialized = json.dumps(emitted, default=str)
        assert "[REDACTED]" in serialized
        for secret in ("1234567", "user@uw.edu", "jsmith42"):
            assert secret not in serialized


@pytest.mark.parametrize("private", [
    "1234567", "user@uw.edu", "netid: jsmith42",
    "(1234567)", "(user@uw.edu)", "(netid: jsmith42)",
    " [1234567], (user@uw.edu)! ", "“1234567”", "((user@uw.edu))",
])
@pytest.mark.parametrize("mode", ["deterministic", "model"])
def test_fully_redacted_api_cli_queries_return_no_results(catalog, monkeypatch, private, mode):
    prompts = []

    class CapturingQuick(QuickModel):
        def invoke(self, messages):
            prompts.append(messages)
            return _heuristic_intent("CSE 142")

    quick, deep = CapturingQuick(), ControlledModel()
    monkeypatch.setattr(factory, "create_tier_client",
                        lambda config, tier: quick if tier == "quick" else deep)
    registry, _ = main._load_registry()
    cfg = replace(catalog, llm_mode=mode)
    monkeypatch.setattr(main, "_load_registry", lambda: (registry, cfg))
    result = CliRunner().invoke(main.app, ["search", private])
    assert result.exit_code == 0, result.output
    actual = json.loads(result.output)
    assert actual["status"] == "not_found"
    assert actual["structured_answer"]["course"] is None
    assert actual["structured_answer"]["ranked_courses"] == []
    assert actual["answer"] == "No matching course found in approved indexed sources."
    assert actual["citations"] == []
    with TestClient(api_app.create_app(cfg)) as client:
        response = client.post("/course-search", json={"query": private})
        assert response.status_code == 200
        assert response.json()["answer_type"] == "no_results"
        assert response.json()["results"] == []
    assert prompts == []
    assert deep.calls == 0


@pytest.mark.parametrize("route,field", [
    ("exact_code", "course_id"), ("department", "department_code"), ("keyword", "keyword"),
])
@pytest.mark.parametrize("missing", [True, False])
@pytest.mark.parametrize("blank", [None, "", " \t "])
def test_incomplete_classification_preserves_api_cli_catalog(catalog, monkeypatch, route, field, missing, blank):
    record = {"intent": route}
    if not missing:
        record[field] = blank
    _assert_classification_catalog(catalog, monkeypatch, record, "CSE courses", "CSE courses")


@pytest.mark.parametrize("course_id", [None, "", " \t "])
def test_exact_classification_normalizes_components(catalog, monkeypatch, course_id):
    _assert_classification_catalog(catalog, monkeypatch, {
        "intent": "exact_code", "course_id": course_id,
        "department_code": " cse ", "course_number": " 142 ",
    }, "explain introductory programming", "CSE 142")


@pytest.mark.parametrize("course_id", ["CSE 142", "CSE-142", " cse   142 ", "cse-142", "CSE 142 A"])
@pytest.mark.parametrize("components", [False, True])
def test_populated_exact_classification_normalizes_ids(catalog, monkeypatch, course_id, components):
    record = {"intent": "exact_code", "course_id": course_id}
    if components:
        record.update(department_code="CSE", course_number="142")
    _assert_classification_catalog(catalog, monkeypatch, record, "explain introductory programming", "CSE 142")


@pytest.mark.parametrize("course_id", ["invalid", "CSE/142", "CSE-14", "CSE-142 extra"])
def test_invalid_populated_exact_classification_falls_back(catalog, monkeypatch, course_id):
    _assert_classification_catalog(catalog, monkeypatch, {
        "intent": "exact_code", "course_id": course_id,
        "department_code": "CSE", "course_number": "142",
    }, "CSE courses", "CSE courses")


@pytest.mark.parametrize("components", [
    {"department_code": "CSE"}, {"course_number": "142"},
    {"department_code": " ", "course_number": "142"},
    {"department_code": "CSE", "course_number": "14"},
])
def test_invalid_exact_components_fall_back(catalog, monkeypatch, components):
    _assert_classification_catalog(catalog, monkeypatch, {
        "intent": "exact_code", **components,
    }, "CSE courses", "CSE courses")


def _assert_classification_catalog(catalog, monkeypatch, record, query, baseline_query):
    quick = Mock()
    quick.with_structured_output.return_value = quick
    quick.invoke.return_value = record
    deep = ControlledModel()
    monkeypatch.setattr(factory, "create_tier_client",
                        lambda config, tier: quick if tier == "quick" else deep)
    registry, _ = main._load_registry()
    cfg = replace(catalog, llm_mode="model")
    monkeypatch.setattr(main, "_load_registry", lambda: (registry, cfg))
    runner = CliRunner()
    baseline = runner.invoke(main.app, ["search", baseline_query, "--llm-mode", "deterministic"])
    assert baseline.exit_code == 0, baseline.output
    expected = json.loads(baseline.output)
    result = runner.invoke(main.app, ["search", query])
    assert result.exit_code == 0, result.output
    actual = json.loads(result.output)
    assert expected["structured_answer"]["course"] or expected["structured_answer"]["ranked_courses"]
    for field in ("course", "ranked_courses", "citations", "freshness", "limitations", "status"):
        assert actual["structured_answer"][field] == expected["structured_answer"][field]
    assert actual["citations"] == expected["citations"]
    with TestClient(api_app.create_app(catalog)) as client:
        baseline_api = client.post("/course-search", json={"query": baseline_query}).json()
    with TestClient(api_app.create_app(cfg)) as client:
        response = client.post("/course-search", json={"query": query})
        assert response.status_code == 200
        assert response.json()["results"] == baseline_api["results"]
        assert response.json()["answer_type"] == baseline_api["answer_type"]
    assert quick.invoke.call_count == deep.calls == 2


@pytest.mark.parametrize("keyword,has_matches", [
    ("object-oriented", False), ("programming", True),
    ('"programming"', True), ("[programming]", True), ("(programming)", True),
    ("programming OR structures", False), ("NOT", False),
    ("NEAR(programming)", False), ("prog*", False), ('"[]():-*', False),
])
def test_model_literal_keywords_api_cli(catalog, monkeypatch, keyword, has_matches):
    quick = Mock()
    quick.with_structured_output.return_value = quick
    quick.invoke.return_value = {"intent": "keyword", "keyword": keyword}
    deep = ControlledModel()
    monkeypatch.setattr(factory, "create_tier_client",
                        lambda config, tier: quick if tier == "quick" else deep)
    registry, _ = main._load_registry()
    cfg = replace(catalog, llm_mode="model")
    monkeypatch.setattr(main, "_load_registry", lambda: (registry, cfg))
    runner = CliRunner()
    baseline = runner.invoke(main.app, ["search", "programming", "--llm-mode", "deterministic"])
    assert baseline.exit_code == 0, baseline.output
    expected = json.loads(baseline.output)
    query = "find object oriented programming courses"
    result = runner.invoke(main.app, ["search", query])
    assert result.exit_code == 0, result.output
    actual = json.loads(result.output)
    if has_matches:
        for field in ("course", "ranked_courses", "citations", "freshness", "status"):
            assert actual["structured_answer"][field] == expected["structured_answer"][field]
        assert actual["citations"] == expected["citations"]
    else:
        assert actual["structured_answer"]["course"] is None
        assert actual["structured_answer"]["ranked_courses"] == []
        assert actual["citations"] == []
        assert actual["status"] == "not_found"
    with TestClient(api_app.create_app(catalog)) as client:
        baseline_api = client.post("/course-search", json={"query": "programming"}).json()
    with TestClient(api_app.create_app(cfg)) as client:
        response = client.post("/course-search", json={"query": query})
        assert response.status_code == 200
        if has_matches:
            assert response.json()["results"] == baseline_api["results"]
            assert response.json()["answer_type"] == baseline_api["answer_type"]
        else:
            assert response.json()["answer_type"] == "no_results"
            assert response.json()["results"] == []
    assert quick.invoke.call_count == 2
    assert deep.calls == (2 if has_matches else 0)
