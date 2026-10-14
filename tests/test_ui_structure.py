import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.theme import PALETTE, TAB_LABELS

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def _all_markdown(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_app_runs_without_exception():
    assert not _app().exception


def test_three_tabs_only():
    at = _app()
    assert [t.label for t in at.tabs] == list(TAB_LABELS)
    assert len(at.tabs) == 3


def test_selector_in_research_tab():
    at = _app()
    research, deck, weekly = at.tabs
    assert [r.label for r in research.radio] == ["Research mode"]
    assert not deck.radio and not weekly.radio
    assert research.radio[0].options == ["Sequential", "Hierarchical"]


def test_deck_tab_disabled_without_report():
    at = _app()
    deck_buttons = at.tabs[1].button
    assert len(deck_buttons) == 1 and deck_buttons[0].disabled is True


def test_weekly_rerun_disabled_and_scheduler_not_claimed():
    at = _app()
    weekly = at.tabs[2]
    assert weekly.button[0].disabled is True
    text = " ".join(m.value for m in weekly.markdown)
    assert "Confirmed configured: no" in text
    assert "none recorded" in text


def test_validation_errors_displayed():
    at = _app()
    at.tabs[0].button[0].click().run()
    assert len(at.error) == 3
    assert not at.exception


def test_workflow_area_is_idle_and_not_simulated():
    at = _app()
    text = _all_markdown(at)
    assert "Live Agent Workflow" in text
    for agent in ("Market Researcher", "Review Analyst", "Strategy Analyst", "Report Writer"):
        assert agent in text
    assert text.count(">Idle<") == 4
    for fake in ("Running", "Completed", "In progress", "Done"):
        assert fake not in text


def test_manager_shown_only_in_hierarchical_mode():
    at = _app()
    assert "Research Manager" not in _all_markdown(at)
    at.radio(key="research_mode").set_value("hierarchical").run()
    assert not at.exception
    text = _all_markdown(at)
    assert "Research Manager" in text and "No delegation recorded" in text
    assert "Not yet implemented (M5)" not in text  # the Manager is real in M5


def test_behind_the_scenes_expander_present_and_empty():
    at = _app()
    labels = [e.label for e in at.expander]
    assert "Engineering Trace" in labels
    text = _all_markdown(at)
    assert "No run has been executed" in text
    assert "Unavailable (nothing measured)" in text


def test_environment_status_shows_names_not_values():
    at = _app()
    text = _all_markdown(at)
    assert "OPENAI_API_KEY" in text and "SERPER_API_KEY" in text and "MODEL_NAME" in text


def test_palette_and_theme_tokens_centralized():
    config = (ROOT / ".streamlit" / "config.toml").read_text("utf-8").lower()
    for token in ("#2dd4bf", "#050c1c", "#e8eef8"):
        assert token in config
    from ui import theme

    for value in PALETTE.values():
        assert value.lower() in theme._CSS.lower()


def test_css_only_in_theme_module():
    for path in (ROOT / "ui").glob("*.py"):
        if path.name == "theme.py":
            continue
        source = path.read_text("utf-8")
        assert "<style" not in source, path.name
        assert not re.search(r'style\s*=\s*["\']', source), path.name


def test_branding_is_launchscout_only():
    text = _all_markdown(_app())
    assert "LaunchScout" in text and "Competitor Research Crew" in text
    assert "From market intelligence to launch strategy." in text
    assert "orchestra" not in text.lower()


def test_flow_order_form_then_workflow_then_behind_the_scenes():
    at = _app()
    text = _all_markdown(at)
    assert text.index("Describe the business idea") < text.index(">Live Agent Workflow<")
