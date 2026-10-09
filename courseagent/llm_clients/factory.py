"""Tiered LLM client factory (DeepSeek default, OpenAI-compatible)."""

from __future__ import annotations

import os
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
        api_key = overrides.pop("api_key", None) or os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeek model mode")
        overrides["api_key"] = api_key
        base_url = config.deepseek_base_url
        model = config.deep_model if tier == "deep" else config.quick_model
    else:
        base_url = overrides.pop("base_url", None)
        model = overrides.pop("model", config.deep_model if tier == "deep" else config.quick_model)

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": 0 if tier == "deep" else 0.1,
        "timeout": 10.0,
        "max_retries": 0,
    }
    if base_url:
        kwargs["base_url"] = base_url
    kwargs.update(overrides)
    return ChatOpenAI(**kwargs)
