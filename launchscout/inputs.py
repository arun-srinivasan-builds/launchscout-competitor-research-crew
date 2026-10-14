"""Form input validation for the Research Workspace."""

from __future__ import annotations

import re

from launchscout.schemas import ResearchInput, ResearchMode

LIMITS: dict[str, tuple[int, int]] = {
    "idea": (5, 300),
    "city": (2, 100),
    "target_customer": (3, 200),
}
MAX_KNOWN_COMPETITORS = 10
MAX_COMPETITOR_NAME = 100

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_SPACES = re.compile(r"[ \t]+")
_SPLIT = re.compile(r"[,\n;]+")

LABELS = {
    "idea": "Business idea",
    "city": "City / target market",
    "target_customer": "Target customer",
    "known_competitors": "Known competitors",
    "mode": "Research mode",
}


class InputValidationError(ValueError):
    """Raised with a per-field error mapping suitable for display."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        super().__init__("; ".join(f"{LABELS.get(k, k)}: {v}" for k, v in errors.items()))


def _normalize(text: str | None) -> str:
    text = _CONTROL.sub("", text or "")
    return _SPACES.sub(" ", text.replace("\r", "\n")).strip()


def parse_known_competitors(raw: str | None) -> list[str]:
    """Split comma/semicolon/newline separated names; trim, drop empties, dedupe by casefold."""
    seen: set[str] = set()
    names: list[str] = []
    for part in _SPLIT.split(_normalize(raw)):
        name = _SPACES.sub(" ", part).strip()
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            names.append(name)
    return names


def validate_input(
    idea: str | None,
    city: str | None,
    target_customer: str | None,
    known_competitors: str | None = "",
    mode: str | ResearchMode = ResearchMode.SEQUENTIAL,
) -> ResearchInput:
    """Validate raw form values. Raises InputValidationError with all field errors at once."""
    errors: dict[str, str] = {}
    values = {
        "idea": _normalize(idea),
        "city": _normalize(city),
        "target_customer": _normalize(target_customer),
    }
    for field, value in values.items():
        lo, hi = LIMITS[field]
        label = LABELS[field]
        if not value:
            errors[field] = f"{label} is required."
        elif len(value) < lo:
            errors[field] = f"{label} must be at least {lo} characters."
        elif len(value) > hi:
            errors[field] = f"{label} must be at most {hi} characters."

    competitors = parse_known_competitors(known_competitors)
    if len(competitors) > MAX_KNOWN_COMPETITORS:
        errors["known_competitors"] = f"Provide at most {MAX_KNOWN_COMPETITORS} known competitors."
    elif any(len(c) > MAX_COMPETITOR_NAME for c in competitors):
        errors["known_competitors"] = (
            f"Each competitor name must be at most {MAX_COMPETITOR_NAME} characters."
        )

    try:
        parsed_mode = ResearchMode(mode)
    except ValueError:
        errors["mode"] = "Choose Sequential or Hierarchical."
        parsed_mode = ResearchMode.SEQUENTIAL

    if errors:
        raise InputValidationError(errors)

    return ResearchInput(
        idea=values["idea"],
        city=values["city"],
        target_customer=values["target_customer"],
        known_competitors=competitors,
        mode=parsed_mode,
    )
