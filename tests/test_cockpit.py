"""Research Intelligence Cockpit prototype: deterministic, read-only, zero-call."""

import hashlib
import time
from pathlib import Path

from streamlit.testing.v1 import AppTest

from launchscout.evidence import EvidenceEntry
from launchscout.runner import set_manager
from launchscout.saved_runs import load_saved_snapshot
from launchscout.schemas import ResearchInput
from tests.conftest import make_manager
from tests.helpers import MENU_URLS, PARTIAL_REPORT_MD, PASS_REPORT_MD, make_executor
from ui import cockpit

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
INPUT = ResearchInput(
    idea="Healthy millet meal boxes", city="Coimbatore", target_customer="office workers"
)


def _make_run(tmp_path, **kwargs):
    manager = make_manager(tmp_path, executor=make_executor(**kwargs))
    run = manager.start(INPUT)
    end = time.time() + 10
    while time.time() < end:
        snap = manager.snapshot(run.paths.run_id)
        if snap and not snap.active:
            break
        time.sleep(0.02)
    while manager.active_run() is not None and time.time() < end:
        time.sleep(0.02)
    return run


def _digest(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _proto(tmp_path, run) -> AppTest:
    """Production app after a restart: select the saved run from the left panel."""
    set_manager(make_manager(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    at.selectbox(key="saved_run_select").set_value(run.paths.run_id).run()
    assert not at.exception
    return at


# ---------------------------------------------------------------- pure helpers


def test_roadmap_parses_block_and_inline_formats():
    weeks = cockpit.parse_roadmap(PASS_REPORT_MD)
    assert [w for w, _t, _a in weeks] == [1, 2, 3, 4]
    assert any("menu" in a.lower() for a in weeks[1][2])

    block = (
        "## 5. 30-Day Launch Plan\n**Week 1 - Validate**\n- Talk to buyers\n- Price test\n\n"
        "**Week 2 — Pilot**\n- Run pilot\n\n"
        "Week 3: Measure\n1. Track orders\n\nWeek 4\n- Decide\n\n## 6. Sources\n- x\n"
    )
    parsed = cockpit.parse_roadmap(block)
    assert [w for w, _t, _a in parsed] == [1, 2, 3, 4]
    assert parsed[0][1] == "Validate" and parsed[0][2] == ["Talk to buyers", "Price test"]
    assert parsed[2][2] == ["Track orders"]
    assert cockpit.parse_roadmap("## nothing here") == []


def test_competitor_rows_are_read_with_their_headers():
    rows = cockpit.competitor_rows(PASS_REPORT_MD)
    assert set(rows) == {"millet kitchen", "green tiffin", "hearty bowls"}
    assert cockpit._cell(rows["millet kitchen"], "strength") == "menu"
    assert cockpit._cell(rows["hearty bowls"], "weak") == "pricey"


def test_source_labels_use_ledger_titles_and_provenance():
    from datetime import date

    ledger = {
        "example.com/menu": EvidenceEntry(
            url="https://www.example.com/menu",
            kind="scraped",
            title="Example Menu",
            accessed_on=date(2026, 10, 14),
        )
    }
    label, origin = cockpit.source_label("https://example.com/menu/", ledger)
    assert label == "Example Menu" and origin == "page read"
    label, origin = cockpit.source_label("https://unknown.example/a/b", ledger)
    assert label == "unknown.example/a/b" and origin == "not in evidence ledger"


def test_source_link_escapes_and_rejects_non_http():
    html = cockpit.source_link('javascript:alert("x")', {})
    assert "<a" not in html
    safe = cockpit.source_link("https://a.example/?q=<script>", {})
    assert "<script>" not in safe and 'rel="noopener noreferrer"' in safe


def test_reasons_are_deduplicated():
    reasons = [
        "only 2 competitor(s) have a name, URL and evidence URL (3 required)",
        "only 0 competitor(s) have a verified price with evidence (3 required)",
        "R2 At least 3 competitor rows: 2 competitor row(s) in the Key Competitors table.",
        "R3 Every URL: 1 URL(s) were never returned by any tool.",
    ]
    out = cockpit._unique_reasons(reasons)
    assert len(out) == 3 and not any("competitor row" in r for r in out)


# ---------------------------------------------------------------- prototype app


def test_prototype_renders_partial_run_with_one_acceptance_statement(tmp_path):
    run = _make_run(tmp_path, report=PARTIAL_REPORT_MD)
    at = _proto(tmp_path, run)
    md = " ".join(m.value for m in at.markdown)
    assert at.selectbox(key="saved_run_select").value == run.paths.run_id
    assert "Crew completed" in md and "Report failed acceptance" in md  # two distinct statements
    assert "Why acceptance did not pass" in md
    # no stacked red banners: the cockpit uses one block, not st.error + a second list
    assert not at.error
    assert md.count("Why acceptance did not pass") == 1
    assert "Quality checks passed" in md and "Competitors with a verified price" in md
    assert at.button(key="run_research").disabled is False  # production: runs stay possible


def test_navigation_shows_six_areas_and_switches_content(tmp_path):
    run = _make_run(tmp_path)
    at = _proto(tmp_path, run)
    assert list(cockpit.AREAS) == [
        "Competitor Landscape",
        "Customer Voice",
        "Market Opportunity",
        "30-Day Launch Roadmap",
        "Evidence & Quality",
        "Engineering Trace",
    ]
    md = " ".join(m.value for m in at.markdown)
    assert "ck-grid" in md and "Millet Kitchen" in md
    for area, marker in (
        ("Customer Voice", "ck-quote"),
        ("Market Opportunity", "Proposed offer"),
        ("30-Day Launch Roadmap", "WEEK 1"),
        ("Evidence & Quality", "Quality checks"),
        ("Engineering Trace", "Model calls"),
    ):
        at.session_state[cockpit.AREA_KEY] = area
        at.run()
        assert not at.exception
        assert marker in " ".join(m.value for m in at.markdown), area


def test_engineering_trace_is_collapsed_and_full_report_on_demand(tmp_path):
    run = _make_run(tmp_path)
    at = _proto(tmp_path, run)
    at.session_state[cockpit.AREA_KEY] = "Engineering Trace"
    at.run()
    trace = next(e for e in at.expander if e.label.startswith("Engineering Trace"))
    assert trace.proto.expanded is False
    full = next(e for e in at.expander if "Full original six-section report" in e.label)
    assert full.proto.expanded is False
    assert {d.proto.label for d in at.get("download_button")} == {
        "Download Markdown",
        "Download PDF",
    }


def test_prototype_is_read_only_and_makes_zero_calls(tmp_path, monkeypatch):
    run = _make_run(tmp_path, report=PARTIAL_REPORT_MD)
    runs = tmp_path / "runs"
    before = {p.name: _digest(p) for p in runs.iterdir() if p.is_dir()}
    hits: list[str] = []

    def trap(name):
        def _fail(*a, **k):
            hits.append(name)
            raise AssertionError(f"{name} called")

        return _fail

    monkeypatch.setattr("launchscout.llm.build_llm", trap("build_llm"))
    monkeypatch.setattr("crewai.LLM.call", trap("LLM.call"))
    monkeypatch.setattr("launchscout.tools._default_search", trap("serper"))
    monkeypatch.setattr("launchscout.tools._default_scrape", trap("scrape"))
    monkeypatch.setattr("launchscout.runner.run_sequential", trap("crew"))

    at = _proto(tmp_path, run)
    for area in cockpit.AREAS:
        at.session_state[cockpit.AREA_KEY] = area
        at.run()
        assert not at.exception, area
    for _ in range(3):
        at.run()
    assert hits == []
    assert {p.name: _digest(p) for p in runs.iterdir() if p.is_dir()} == before


def test_legacy_run_renders_without_validation(tmp_path):
    run = _make_run(tmp_path)
    for name in ("validation.json", "report.pdf", "report.writer.md"):
        (run.paths.root / name).unlink()
    at = _proto(tmp_path, run)
    assert not at.exception
    md = " ".join(m.value for m in at.markdown)
    assert "Acceptance not evaluated" in md and "saved before report validation existed" in md
    snap = load_saved_snapshot(tmp_path / "runs", run.paths.run_id)
    assert snap.validation is None


def test_production_app_renders_cockpit_not_the_old_results_page(tmp_path):
    run = _make_run(tmp_path)
    at = _proto(tmp_path, run)
    md = " ".join(m.value for m in at.markdown)
    assert "ck-hero" in md and "URLs discovered" in md and "Pages read" in md
    labels = [e.label for e in at.expander]
    assert "Behind the Scenes" not in labels and "Report quality evaluation" not in labels
    assert any(label.startswith("Full original six-section report") for label in labels)
    assert not any("Sources retrieved" in m.value for m in at.markdown)
    assert MENU_URLS  # fixture import used
