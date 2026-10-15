"""LLM construction from environment settings. No model is ever substituted silently."""

from __future__ import annotations

from typing import Any

from launchscout.config import MODEL_ENV, Settings
from launchscout.demo import require_live


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


def crewai_model_string(model_name: str) -> str:
    """CrewAI/LiteLLM-style identifier for an OpenAI model name."""
    return model_name if "/" in model_name else f"openai/{model_name}"


def build_llm(settings: Settings) -> Any:
    """Build a CrewAI LLM using exactly the configured model name."""
    require_live("Model access")
    if settings.model_name is None:
        raise ConfigError(f"{MODEL_ENV} is not set; refusing to pick a default model.")
    if settings.openai_api_key is None:
        raise ConfigError("OPENAI_API_KEY is not set.")
    from crewai import LLM

    return LLM(
        model=crewai_model_string(settings.model_name),
        api_key=settings.openai_api_key.get_secret_value(),
    )
