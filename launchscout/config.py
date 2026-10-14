"""Environment configuration. Keys are read by name; values are never logged or displayed."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, SecretStr

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LLM_KEY_ENV = "OPENAI_API_KEY"
SERPER_KEY_ENV = "SERPER_API_KEY"
MODEL_ENV = "MODEL_NAME"

_PLACEHOLDER_PREFIXES = ("your", "xxx", "changeme", "<", "replace")


def _clean(value: str | None) -> str | None:
    """Return a stripped value, or None if blank or an obvious placeholder."""
    if value is None:
        return None
    value = value.strip().strip('"').strip("'")
    if not value or value.lower().startswith(_PLACEHOLDER_PREFIXES):
        return None
    return value


class RunLimits(BaseModel):
    """Bounded-execution limits (PRP guardrail G5). Defaults are deliberately conservative."""

    max_searches: int = 12
    max_scrapes: int = 10
    # Per-agent share of the totals above, so one researcher cannot starve the other.
    searches_per_agent: int = 6
    scrapes_per_agent: int = 5
    search_results: int = 6
    scrape_max_chars: int = 6000
    agent_max_iter: int = 8
    agent_timeout_s: int = 420
    tool_retries: int = 1
    run_timeout_s: int = 1200
    # Hard stop on model calls per run (observed runs used 10-13; see LLM audit).
    max_llm_calls: int = 40
    # Hierarchical runs add Manager calls, so they get a larger total but a hard Manager cap.
    max_llm_calls_hierarchical: int = 45
    max_manager_llm_calls: int = 16
    max_delegations: int = 8
    manager_max_iter: int = 10
    cancel_grace_s: int = 60


class Settings(BaseModel):
    """Runtime settings. Secret fields use SecretStr so repr/str never reveal values."""

    openai_api_key: SecretStr | None = None
    serper_api_key: SecretStr | None = None
    model_name: str | None = None

    def key_presence(self) -> dict[str, bool]:
        """Presence of each required variable, by name only."""
        return {
            LLM_KEY_ENV: self.openai_api_key is not None,
            SERPER_KEY_ENV: self.serper_api_key is not None,
            MODEL_ENV: self.model_name is not None,
        }

    def missing(self) -> list[str]:
        """Names of required variables that are not set."""
        return [name for name, present in self.key_presence().items() if not present]


def load_settings(
    env: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> Settings:
    """Load settings from a mapping, else from `.env` (if present) overlaid by the process env.

    Process environment variables take precedence over `.env` values.
    """
    if env is None:
        path = dotenv_path if dotenv_path is not None else PROJECT_ROOT / ".env"
        merged: dict[str, str | None] = {}
        if path.is_file():
            merged.update(dotenv_values(path))
        merged.update({k: v for k, v in os.environ.items() if k in _KNOWN})
        source: Mapping[str, str | None] = merged
    else:
        source = env

    llm_key = _clean(source.get(LLM_KEY_ENV))
    serper_key = _clean(source.get(SERPER_KEY_ENV))
    return Settings(
        openai_api_key=SecretStr(llm_key) if llm_key else None,
        serper_api_key=SecretStr(serper_key) if serper_key else None,
        model_name=_clean(source.get(MODEL_ENV)),
    )


_KNOWN = {LLM_KEY_ENV, SERPER_KEY_ENV, MODEL_ENV}
