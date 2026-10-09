"""Shared model construction for API and CLI workflows."""

from __future__ import annotations

from config.default_config import DefaultConfig
from courseagent.graph.course_graph import CourseResearchGraph
from courseagent.llm_clients import factory


def create_graph(config: DefaultConfig) -> CourseResearchGraph:
    """Use the supported configured provider when model mode is selected.

    Missing credentials or initialization failure leave both tiers deterministic.
    Client transport timeouts and disabled retries bound provider waits; each
    node handles invocation errors by returning its deterministic result.
    """

    quick_llm = deep_llm = None
    if config.llm_mode == "model" and config.llm_provider.lower() == "deepseek":
        try:
            quick_llm = factory.create_tier_client(config, "quick")
            deep_llm = factory.create_tier_client(config, "deep")
        except Exception:  # noqa: BLE001 - model initialization is optional
            quick_llm = deep_llm = None
    return CourseResearchGraph(config=config, quick_llm=quick_llm, deep_llm=deep_llm)
