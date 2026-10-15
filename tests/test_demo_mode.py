"""Public demo mode: paid execution is impossible (enforced below the UI) and demo data is safe."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from launchscout import demo
from launchscout.config import Settings
from launchscout.demo import DemoModeError
from launchscout.runner import RunManager, set_manager
from launchscout.saved_runs import list_saved_runs, load_saved_snapshot
from launchscout.schemas import ResearchInput
from tests.helpers import tracking_values

ROOT = Path(__file__).resolve().parent.parent
DEMO_RUNS = ROOT / "demo_data" / "saved_runs"
APP = str(ROOT / "app.py")
L5 = "20261014-140643-cold-pressed-juice-subscriptio-3824"
L6 = "20261014-201109-cold-pressed-juice-subscriptio-c0fe"
INPUT = ResearchInput(idea="x idea", city="y city", target_customer="z customers")


@pytest.fixture
def demo_env(monkeypatch):
    monkeypatch.setenv(demo.MODE_ENV, "demo")
    monkeypatch.setenv(demo.RUNS_DIR_ENV, str(DEMO_RUNS))
    for name in ("OPENAI_API_KEY", "SERPER_API_KEY", "MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)
    set_manager(None)
    yield
    set_manager(None)


def _trap(monkeypatch):
    hits: list[str] = []

    def trap(name):
        def _fail(*a, **k):
            hits.append(name)
            raise AssertionError(name)

        return _fail

    monkeypatch.setattr("crewai.LLM.call", trap("LLM.call"))
    monkeypatch.setattr("crewai.Crew.kickoff", trap("kickoff"))
    return hits


# ------------------------------------------------------------------ enforcement (not UI-only)
def test_mode_fails_closed_and_live_needs_an_explicit_setting(monkeypatch, tmp_path):
    monkeypatch.setattr(demo, "PROJECT_ROOT", tmp_path)  # no .env here
    monkeypatch.delenv(demo.MODE_ENV, raising=False)
    assert demo.is_demo() is True
    for value in ("", "demo", " DEMO ", "livee", "true", "1", "production"):
        monkeypatch.setenv(demo.MODE_ENV, value)
        assert demo.is_demo() is True, value
    monkeypatch.setenv(demo.MODE_ENV, " LIVE ")
    assert demo.is_demo() is False


def test_live_can_come_from_a_local_env_file_but_the_environment_wins(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("LAUNCHSCOUT_MODE=live\n", encoding="utf-8")
    monkeypatch.setattr(demo, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv(demo.MODE_ENV, raising=False)
    assert demo.is_demo() is False
    monkeypatch.setenv(demo.MODE_ENV, "demo")
    assert demo.is_demo() is True


def test_run_manager_refuses_to_start_a_run_in_demo(demo_env):
    manager = RunManager()
    with pytest.raises(DemoModeError):
        manager.start(INPUT)
    assert manager.active_run() is None and manager.latest_run_id() is None


def test_model_search_scrape_crew_deck_and_model_check_are_blocked(demo_env, monkeypatch):
    from launchscout import crew, deck, llm, model_check, tools

    settings = Settings(
        openai_api_key="sk-test-not-real", serper_api_key="serper-test", model_name="m"
    )
    with pytest.raises(DemoModeError):
        llm.build_llm(settings)
    with pytest.raises(DemoModeError):
        tools._default_search("anything", 3)
    with pytest.raises(DemoModeError):
        tools._default_scrape("https://example.com")
    with pytest.raises(DemoModeError):
        crew.run_crew(INPUT, settings, None, None, None)  # type: ignore[arg-type]
    with pytest.raises(DemoModeError):
        model_check.main()
    source = deck.load_deck_source(DEMO_RUNS, L6)
    with pytest.raises(DemoModeError):
        deck.generate_deck(source, settings)  # no injected kickoff: a real model call


def test_runs_dir_override_points_the_manager_at_demo_data(demo_env):
    assert RunManager().runs_dir() == DEMO_RUNS


# ------------------------------------------------------------------ the demo experience
def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def _page_text(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_demo_ui_opens_on_a_saved_run_with_replay_and_no_run_button(demo_env, monkeypatch):
    hits = _trap(monkeypatch)
    at = _app()
    assert not at.exception
    assert "Public Demo: Live research and deck generation are disabled" in _page_text(at)
    assert at.button(key="run_research").disabled is True
    assert at.selectbox(key="saved_run_select").value == L6  # newest curated run is shown
    for key in ("replay_restart", "replay_back", "replay_play", "replay_forward"):
        assert at.button(key=key)
    at.button(key="replay_restart").click().run()
    at.button(key="replay_forward").click().run()
    assert at.session_state["replay_pos"] == 1 and not at.exception
    at.selectbox(key="saved_run_select").set_value(L5).run()
    assert not at.exception and at.session_state["replay_run"] == L5
    assert hits == []


def test_demo_notices_are_shown_in_the_header_banner_workspace_and_deck_tab(demo_env):
    at = _app()
    page = _page_text(at)
    assert not at.exception
    for text in (
        "DEMO MODE",
        "Showcasing real saved results",
        "No API usage",
        "Public Demo: Live research and deck generation are disabled on this deployment.",
        "This demo showcases saved research runs only. No new research is executed and no "
        "API calls are made.",
        "Public Demo: Live research is disabled. Pick a saved run below.",
        "Explore real research results, replay the agent workflows and download the reports "
        "and pitch decks.",
        "Public demo: live research is disabled. Pick a saved run below.",
        "Public demo: new pitch deck generation is disabled. Download the existing deck below.",
    ):
        assert text in page, text
    assert not at.info and not at.caption or all("Public demo" not in c.value for c in at.caption)
    assert at.button(key="run_research").disabled is True
    assert at.button(key="deck_generate").disabled is True


def test_demo_deck_source_card_does_not_mention_a_model_call(demo_env):
    at = _app()
    text = " ".join(m.value for m in at.tabs[1].markdown)
    assert (
        "This demo uses a previously generated pitch deck. No new AI calls or research "
        "searches are performed." in text
    )
    assert "Generating makes one model call" not in text


def test_live_mode_shows_no_demo_notices(monkeypatch, tmp_path):
    monkeypatch.setenv(demo.MODE_ENV, "live")
    monkeypatch.setenv(demo.RUNS_DIR_ENV, str(DEMO_RUNS))
    set_manager(None)
    try:
        at = _app()
    finally:
        set_manager(None)
    page = _page_text(at)
    assert not at.exception
    assert "DEMO MODE" not in page and "Public Demo" not in page and "Public demo" not in page
    assert at.button(key="run_research").disabled is False
    deck_text = " ".join(m.value for m in at.tabs[1].markdown)
    assert "Generating makes one model call (no searches, no page reads)." in deck_text
    assert "previously generated pitch deck" not in deck_text


def test_demo_blocks_submit_even_if_the_form_is_driven_directly(demo_env, monkeypatch):
    hits = _trap(monkeypatch)
    at = _app()
    at.text_input[0].set_value("some idea")
    at.text_input[1].set_value("some city")
    at.text_input[2].set_value("some customer")
    at.run()
    # the button is disabled, so drive the submit path itself
    from ui import research_tab

    notices: list[tuple[str, str]] = []
    research_tab._handle_submit(
        research_tab.ResearchMode.SEQUENTIAL,
        ("some idea", "some city", "some customer", ""),
        notices,
    )
    assert notices and notices[0][0] == "warning" and "Public demo" in notices[0][1]
    assert RunManager().latest_run_id() is None
    assert hits == []


def test_demo_deck_tab_downloads_existing_deck_but_cannot_generate(demo_env, monkeypatch):
    hits = _trap(monkeypatch)
    at = _app()
    deck_tab = at.tabs[1]
    assert deck_tab.button(key="deck_generate").disabled is True
    text = " ".join(m.value for m in deck_tab.markdown)
    assert "Editable PPTX ready" in text or "Generated deck" in text
    assert hits == []


def test_demo_tracking_shows_the_l5_l6_comparison_with_no_verified_changes(demo_env):
    at = _app()
    tab = at.tabs[2]
    text = " ".join(m.value for m in tab.markdown)
    assert "Comparison available" in text
    values = tracking_values(tab.markdown)
    assert values["Verified changes"] == "0" and values["Needs review"] == "2"
    assert values["Newly observed"] == "0" and values["Not observed in latest run"] == "0"


# ------------------------------------------------------------------ demo data safety
ALLOWED_FILES = {
    "competitors.json",
    "events.jsonl",
    "evidence.json",
    "grounding.json",
    "input.json",
    "metadata.json",
    "report.writer.md",
    "report-PARTIAL.md",
    "report-PARTIAL.pdf",
    "reviews.json",
    "strategy.json",
    "validation.json",
    "report.md",
    "report.pdf",
}
ALLOWED_DECK = {"deck_meta.json", "deck_spec.json", "launchscout-pitch-deck-PARTIAL.pptx"}


def test_demo_data_contains_only_the_approved_runs_and_files():
    assert {p.name for p in DEMO_RUNS.iterdir()} == {L5, L6}
    for run in DEMO_RUNS.iterdir():
        for item in run.iterdir():
            if item.is_dir():
                assert item.name == "deck"
                assert {f.name for f in item.iterdir()} <= ALLOWED_DECK
            else:
                assert item.name in ALLOWED_FILES, item.name


def test_demo_data_has_no_credentials_or_local_paths():
    patterns = [
        re.compile(rb"sk-[A-Za-z0-9_\-]{20,}"),
        re.compile(rb"serper.{0,20}[0-9a-f]{40}", re.I),
        re.compile(rb"[A-Za-z]:\\\\Users", re.I),
        re.compile(rb"[A-Za-z]:\\Users", re.I),
        re.compile(rb"agentic-coding-labs", re.I),
    ]
    offenders = []
    for path in DEMO_RUNS.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            if any(p.search(data) for p in patterns):
                offenders.append(str(path.relative_to(DEMO_RUNS)))
    assert offenders == []
    env_file = ROOT / ".env"
    if env_file.is_file():  # the real key values must not appear either (checked, not printed)
        values = [
            line.partition("=")[2].strip().strip("\"'")
            for line in env_file.read_text("utf-8").splitlines()
            if "KEY" in line.partition("=")[0] and "=" in line
        ]
        blobs = [p.read_bytes() for p in DEMO_RUNS.rglob("*") if p.is_file()]
        for value in values:
            if len(value) >= 8:
                assert not any(value.encode() in blob for blob in blobs)


def test_demo_runs_load_and_match_recorded_metrics():
    snaps = {s.run_id: s for s in list_saved_runs(DEMO_RUNS)}
    assert set(snaps) == {L5, L6}
    l5 = load_saved_snapshot(DEMO_RUNS, L5)
    l6 = load_saved_snapshot(DEMO_RUNS, L6)
    assert (l5.usage.llm_calls, l5.usage.total_tokens) == (13, 69095)
    assert (l6.usage.llm_calls, l6.usage.total_tokens) == (18, 75446)
    meta = json.loads((DEMO_RUNS / L6 / "deck" / "deck_meta.json").read_text("utf-8"))
    assert meta["usage"]["total_tokens"] == 4486 and meta["usage"]["llm_calls"] == 1
