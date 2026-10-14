"""Test isolation: no test may start a live (billable) research run or touch ./runs."""

from __future__ import annotations

import pytest

from launchscout.config import RunLimits
from launchscout.runner import RunManager, set_manager
from tests.helpers import FAKE_SETTINGS, fake_scrape, fake_search, make_executor


def make_manager(tmp_path, **kwargs) -> RunManager:
    options = {
        "runs_dir": tmp_path / "runs",
        "executor": make_executor(),
        "limits": RunLimits(tool_retries=0),
        "settings_loader": lambda: FAKE_SETTINGS,
        "search_impl": fake_search,
        "scrape_impl": fake_scrape,
    }
    options.update(kwargs)
    return RunManager(**options)


@pytest.fixture(autouse=True)
def isolated_manager(tmp_path, monkeypatch):
    monkeypatch.setenv("LAUNCHSCOUT_NO_LIVE", "1")
    manager = make_manager(tmp_path)
    set_manager(manager)
    yield manager
    set_manager(None)
