"""UI behaviour around real (stubbed-executor) runs: start, live state, results, guards."""

import threading
from pathlib import Path

from streamlit.testing.v1 import AppTest

from launchscout.runner import set_manager
from tests.conftest import make_manager
from tests.helpers import make_executor, wait_idle

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def _fill(at: AppTest, mode: str | None = None) -> None:
    research = at.tabs[0]
    research.text_input[0].set_value("Healthy millet meal boxes delivered for lunch")
    research.text_input[1].set_value("Coimbatore")
    research.text_input[2].set_value("office workers aged 25-40")
    if mode:
        at.radio(key="research_mode").set_value(mode)


def _markdown(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def _wait_idle(manager, timeout: float = 90.0) -> None:
    wait_idle(manager, timeout)


def test_run_starts_in_background_and_ui_shows_running_state(tmp_path):
    gate = threading.Event()
    manager = make_manager(tmp_path, executor=make_executor(gate=gate))
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    assert not at.exception
    assert manager.active_run() is not None
    # input panel in its running state: Run disabled, Cancel offered, form still visible
    assert at.button(key="run_research").disabled is True
    assert at.button(key="cancel_run") is not None
    text = _markdown(at)
    assert "Run in progress" in text or "Stopping" in text
    assert "Running:" in text
    gate.set()
    _wait_idle(manager)


def test_results_and_behind_the_scenes_after_completion(tmp_path):
    manager = make_manager(tmp_path)
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    _wait_idle(manager)
    at.run()
    assert not at.exception
    assert "Report validated" in " ".join(m.value for m in at.markdown)
    at.session_state["cockpit_area"] = "Engineering Trace"
    at.run()
    text = _markdown(at)
    assert "Acceptance:</b> pass (validated_pass)" in text
    assert at.button(key="run_research").disabled is False
    run_id = manager.latest_run_id()
    assert run_id and (tmp_path / "runs" / run_id / "events.jsonl").is_file()


def test_session_run_state_persists_across_reruns(tmp_path):
    manager = make_manager(tmp_path)
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    _wait_idle(manager)
    at.run()
    again = at.run()
    assert again.session_state["active_run_id"] == manager.latest_run_id()
    assert "Run " in _markdown(again)


def test_second_session_sees_same_run_and_cannot_duplicate(tmp_path):
    gate = threading.Event()
    manager = make_manager(tmp_path, executor=make_executor(gate=gate))
    set_manager(manager)
    first = _app()
    _fill(first)
    first.button(key="run_research").click().run()
    other = _app()  # a fresh browser session
    assert other.button(key="run_research").disabled is True
    assert "Run in progress" in _markdown(other) or "Stopping" in _markdown(other)
    gate.set()
    _wait_idle(manager)


def test_hierarchical_run_is_started_through_the_same_manager(tmp_path):
    manager = make_manager(tmp_path)
    set_manager(manager)
    at = _app()
    _fill(at, mode="hierarchical")
    at.button(key="run_research").click().run()
    assert any("milestone M5" in i.value for i in at.info) is False
    assert manager.latest_run_id() is not None
    assert manager.snapshot(manager.latest_run_id()).mode.value == "hierarchical"


def test_missing_configuration_blocks_run(tmp_path):
    from launchscout.config import Settings

    manager = make_manager(tmp_path, settings_loader=lambda: Settings())
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    assert any("Missing configuration" in e.value for e in at.error)
    assert manager.latest_run_id() is None


def test_failed_run_shows_error_not_results(tmp_path):
    def boom(run):
        raise RuntimeError("provider unavailable")

    manager = make_manager(tmp_path, executor=boom)
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    _wait_idle(manager)
    at.run()
    assert "The run failed before a report could be produced." in " ".join(
        m.value for m in at.markdown
    )
    assert not at.exception
