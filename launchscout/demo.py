"""Public demo mode: saved research can be explored and replayed, but nothing paid can run.

Demo mode is enforced where paid work would start (run start, model construction, search and
scrape tools, crew execution, deck generation), not only in the UI. It fails closed:
anything other than an explicit `LAUNCHSCOUT_MODE=live` (unset, empty, "demo", a typo) is demo.
The container image sets `demo`. There is no administrative live-research path in a demo
deployment and no credentials are required.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODE_ENV = "LAUNCHSCOUT_MODE"
RUNS_DIR_ENV = "LAUNCHSCOUT_RUNS_DIR"
DEMO_NOTICE = (
    "Public demo: live research and deck generation are disabled on this deployment. Explore "
    "the saved runs, replay the workflows and download the existing reports and decks."
)


class DemoModeError(RuntimeError):
    """A paid or live action was requested while demo mode is active."""


def configured_mode() -> str:
    """`live` or `demo`. Process environment wins over a local `.env`; default is `demo`."""
    value = os.environ.get(MODE_ENV)
    if value is None:
        try:
            value = dotenv_values(PROJECT_ROOT / ".env").get(MODE_ENV)
        except OSError:
            value = None
    return "live" if (value or "").strip().lower() == "live" else "demo"


def is_demo() -> bool:
    """True unless live research was explicitly enabled with `LAUNCHSCOUT_MODE=live`."""
    return configured_mode() != "live"


def require_live(action: str) -> None:
    """Raise `DemoModeError` if `action` (anything that can cost money) is attempted in demo."""
    if is_demo():
        raise DemoModeError(f"{action} is disabled in public demo mode.")


def configured_runs_dir() -> Path | None:
    """Saved-run directory override (the demo image points this at its bundled demo data)."""
    value = os.environ.get(RUNS_DIR_ENV, "").strip()
    return Path(value) if value else None
