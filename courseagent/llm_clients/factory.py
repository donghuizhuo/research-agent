"""Tiered LLM client factory (DeepSeek default, OpenAI-compatible)."""

from __future__ import annotations

from typing import Any, Literal

from langchain_openai import ChatOpenAI

from config.default_config import DefaultConfig

Tier = Literal["deep", "quick"]


def create_tier_client(config: DefaultConfig, tier: Tier, **overrides: Any) -> ChatOpenAI:
    """Return a LangChain ChatOpenAI client for the requested tier.

    Defaults to DeepSeek via its OpenAI-compatible endpoint. Overrides allow
    callers to swap the provider/model or pass an API key directly.
    """

    if config.llm_provider.lower() == "deepseek":
        base_url = config.deepseek_base_url
        model = config.deep_model if tier == "deep" else config.quick_model
    else:
        base_url = overrides.pop("base_url", None)
        model = overrides.pop("model", config.deep_model if tier == "deep" else config.quick_model)

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": 0 if tier == "deep" else 0.1,
    }
    if base_url:
        kwargs["base_url"] = base_url
    kwargs.update(overrides)
    return ChatOpenAI(**kwargs)
