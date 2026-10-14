"""LLM-efficiency standards: non-AI actions never trigger model calls; budgets are enforced."""

import ast
import threading
import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from launchscout.config import RunLimits
from launchscout.runner import input_key, set_manager
from launchscout.schemas import ResearchInput
from tests.conftest import make_manager
from tests.helpers import make_executor

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
INPUT = ResearchInput(
    idea="Healthy millet meal boxes", city="Coimbatore", target_customer="office workers"
)


class Counting:
    """Executor wrapper: counts how many times a (billable) crew execution is started."""

    def __init__(self, inner):
        self.inner = inner
        self.calls = 0

    def __call__(self, run):
        self.calls += 1
        self.inner(run)


@pytest.fixture
def llm_sentinel(monkeypatch):
    """Fail the test if anything builds an LLM or invokes one outside a counted executor."""
    built = []

    def fake_build(settings):
        built.append(1)
        raise AssertionError("an LLM was constructed by a non-AI action")

    monkeypatch.setattr("launchscout.llm.build_llm", fake_build)
    monkeypatch.setattr("launchscout.crew.build_llm", fake_build)

    def no_call(self, *a, **k):
        raise AssertionError("crewai.LLM.call invoked by a non-AI action")

    monkeypatch.setattr("crewai.LLM.call", no_call)
    return built


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def _fill(at: AppTest) -> None:
    r = at.tabs[0]
    r.text_input[0].set_value("Healthy millet meal boxes delivered for lunch")
    r.text_input[1].set_value("Coimbatore")
    r.text_input[2].set_value("office workers aged 25-40")


def _wait_idle(manager, timeout=10.0):
    end = time.time() + timeout
    while manager.active_run() is not None and time.time() < end:
        time.sleep(0.02)


def test_reruns_polling_and_tab_rendering_make_no_llm_calls(tmp_path, llm_sentinel):
    counter = Counting(make_executor())
    manager = make_manager(tmp_path, executor=counter)
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    _wait_idle(manager)
    assert counter.calls == 1
    for _ in range(4):  # UI reruns, fragment polling, all three tabs rendered each time
        at.run()
    assert counter.calls == 1
    assert llm_sentinel == []


def test_polling_an_active_run_does_not_restart_it(tmp_path, llm_sentinel):
    gate = threading.Event()
    counter = Counting(make_executor(gate=gate))
    manager = make_manager(tmp_path, executor=counter)
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    for _ in range(3):
        at.run()
    assert counter.calls == 1
    gate.set()
    _wait_idle(manager)


def test_deck_and_weekly_tabs_never_start_runs(tmp_path, llm_sentinel, monkeypatch):
    manager = make_manager(tmp_path)

    def forbidden(*a, **k):
        raise AssertionError("a run was started by a non-research action")

    monkeypatch.setattr(manager, "start", forbidden)
    set_manager(manager)
    at = _app()
    assert not at.exception
    assert len(at.tabs) == 3
    assert llm_sentinel == []


def test_identical_input_reuses_completed_run_until_explicit_rerun(tmp_path, llm_sentinel):
    counter = Counting(make_executor())
    manager = make_manager(tmp_path, executor=counter)
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    _wait_idle(manager)
    at.run()
    first_run = manager.latest_run_id()
    assert counter.calls == 1

    at.button(key="run_research").click().run()  # same input again
    assert counter.calls == 1, "identical input must not start a second run"
    assert any("identical research run" in i.value for i in at.info)
    assert manager.latest_run_id() == first_run

    at.button(key="run_again").click().run()  # explicit, deliberate re-run
    _wait_idle(manager)
    assert counter.calls == 2
    assert manager.latest_run_id() != first_run


def test_input_identity_ignores_case_spacing_and_competitor_order(tmp_path):
    manager = make_manager(tmp_path)
    run = manager.start(
        INPUT.model_copy(update={"known_competitors": ["Acme", "Beta Foods"]})
    )
    _wait_idle(manager)
    same = ResearchInput(
        idea="  healthy MILLET   meal boxes ",
        city="coimbatore",
        target_customer="Office Workers",
        known_competitors=["beta foods", "ACME"],
    )
    assert input_key(same) == input_key(run.input)
    assert manager.find_reusable(same) == run.paths.run_id
    different = same.model_copy(update={"city": "Chennai"})
    assert manager.find_reusable(different) is None


def test_failed_or_cancelled_runs_are_never_reused(tmp_path):
    def boom(run):
        raise RuntimeError("provider unavailable")

    manager = make_manager(tmp_path, executor=boom)
    manager.start(INPUT)
    _wait_idle(manager)
    assert manager.find_reusable(INPUT) is None


def test_llm_call_limit_stops_the_run(tmp_path):
    def chatty(run):
        for _ in range(10):
            if run.ctx.cancel_event.is_set():
                return
            run.collector.emit("llm_completed", "call", "Market Researcher", status="ok")
            time.sleep(0.01)
        run.record_output("Competitor research", "{}")

    manager = make_manager(
        tmp_path, executor=chatty, limits=RunLimits(max_llm_calls=3, tool_retries=0)
    )
    run = manager.start(INPUT)
    _wait_idle(manager)
    snap = manager.snapshot(run.paths.run_id)
    assert snap.status in ("partial", "failed")
    assert "LLM call limit" in (snap.error or "")
    assert any(e.kind == "run_budget_stop" for e in snap.events)
    assert 3 < len([e for e in snap.events if e.kind == "llm_completed"]) <= 6


def test_tool_outcomes_and_per_agent_metrics_are_measured(tmp_path):
    manager = make_manager(tmp_path)
    run = manager.start(INPUT)
    _wait_idle(manager)
    snap = manager.snapshot(run.paths.run_id)
    metrics = snap.agent_metrics()
    market = metrics["Market Researcher"]
    assert market["llm_calls"] == 1 and market["total_tokens"] == 120
    assert market["tool_calls"] == 2
    assert market["executed"] >= 1
    assert market["tool_ms"] >= 0
    assert sum(m["total_tokens"] for m in metrics.values()) == snap.usage.total_tokens
    assert snap.usage.llm_calls == 4


def test_crewai_cache_answers_are_counted_not_hidden(tmp_path):
    def executor(run):
        run.collector.emit("tool_started", "search_the_web: q", "Market Researcher", tool="x")
        run.collector.emit("tool_started", "search_the_web: q", "Market Researcher", tool="x")
        run.ctx.search("q")  # only one reaches our tool; the other was a cache answer

    manager = make_manager(tmp_path, executor=executor)
    run = manager.start(INPUT)
    _wait_idle(manager)
    assert manager.snapshot(run.paths.run_id).usage.cache_hits == 1


DETERMINISTIC_MODULES = [
    "grounding", "evidence", "progress", "runs", "inputs", "schemas", "config", "logging_utils",
]
FORBIDDEN_IMPORTS = ("crewai", "openai", "litellm", "langchain", "launchscout.llm",
                     "launchscout.crew", "launchscout.agents", "launchscout.tasks")


@pytest.mark.parametrize("module", DETERMINISTIC_MODULES)
def test_deterministic_modules_import_no_llm_code(module):
    tree = ast.parse((ROOT / "launchscout" / f"{module}.py").read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    bad = [m for m in imported if m.startswith(FORBIDDEN_IMPORTS)]
    assert not bad, f"{module} must stay deterministic; imports {bad}"
