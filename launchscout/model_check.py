"""Model compatibility verification.

Two separate, honestly labelled checks:
  1. API availability: asks the provider whether the configured model id exists for the
     configured key (a real network call, only when a key and model name are present).
  2. CrewAI compatibility: constructs a crewai LLM object for the model id. This verifies
     construction only; it does NOT make a completion request.

Run: python -m launchscout.model_check
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel

from launchscout.config import MODEL_ENV, Settings, load_settings
from launchscout.llm import build_llm
from launchscout.logging_utils import get_logger

log = get_logger(__name__)

Status = Literal["not_configured", "skipped_no_key", "available", "unavailable", "error"]


class ModelCheckResult(BaseModel):
    status: Status
    model_name: str | None
    detail: str
    live_call_made: bool = False
    crewai_construction: Literal["ok", "failed", "not_attempted"] = "not_attempted"
    crewai_detail: str = ""


def _default_client_factory(api_key: str) -> Any:
    from openai import OpenAI

    return OpenAI(api_key=api_key, timeout=20.0, max_retries=1)


def check_model(
    settings: Settings,
    client_factory: Callable[[str], Any] | None = None,
) -> ModelCheckResult:
    """Check model availability (live) and CrewAI construction. Never substitutes a model."""
    if settings.model_name is None:
        return ModelCheckResult(
            status="not_configured",
            model_name=None,
            detail=f"{MODEL_ENV} is not set. No model is assumed or substituted.",
        )
    if settings.openai_api_key is None:
        return ModelCheckResult(
            status="skipped_no_key",
            model_name=settings.model_name,
            detail="OPENAI_API_KEY is not set; the live availability check was not executed.",
        )

    factory = client_factory or _default_client_factory
    try:
        client = factory(settings.openai_api_key.get_secret_value())
        client.models.retrieve(settings.model_name)
        result = ModelCheckResult(
            status="available",
            model_name=settings.model_name,
            detail="Provider confirmed the model id exists for this key.",
            live_call_made=True,
        )
    except Exception as exc:  # noqa: BLE001 - report class/status only, never message text
        code = getattr(exc, "status_code", None)
        name = type(exc).__name__
        if code == 404 or name == "NotFoundError":
            status: Status = "unavailable"
            detail = "Provider reports this model id is not available to this key."
        else:
            status = "error"
            detail = f"Availability check failed ({name}" + (f", HTTP {code})" if code else ")")
        log.warning("model check: %s", detail)
        result = ModelCheckResult(
            status=status, model_name=settings.model_name, detail=detail, live_call_made=True
        )

    if result.status == "available":
        try:
            build_llm(settings)
            result.crewai_construction = "ok"
            result.crewai_detail = "crewai.LLM constructed (no completion requested)."
        except Exception as exc:  # noqa: BLE001
            result.crewai_construction = "failed"
            result.crewai_detail = f"crewai.LLM construction failed ({type(exc).__name__})."
    return result


def main() -> int:
    from launchscout.demo import require_live

    require_live("The live model check")
    settings = load_settings()
    result = check_model(settings)
    sys.stdout.write(
        f"status={result.status}\nmodel={result.model_name}\n"
        f"live_call_made={result.live_call_made}\ndetail={result.detail}\n"
        f"crewai_construction={result.crewai_construction} {result.crewai_detail}\n"
    )
    return 0 if result.status == "available" else 1


if __name__ == "__main__":
    raise SystemExit(main())
