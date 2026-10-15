"""M7 competitor change tracking: deterministic, offline comparison of saved runs.

All fixtures here are SYNTHETIC test data (invented competitors and prices) written to tmp
directories; they are never shown in the application.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from launchscout.runner import set_manager
from launchscout.saved_runs import load_saved_snapshot
from launchscout.schemas import Competitor, CompetitorSet, Price, ResearchInput
from launchscout.tracking import (
    CHANGED,
    NEW,
    NOT_OBSERVED,
    REVIEW,
    UNCHANGED,
    compare_snapshots,
    price_change,
    to_markdown,
)
from launchscout.validation import ValidationReport
from tests.conftest import make_manager
from tests.helpers import tracking_values

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
T0 = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
INPUT = ResearchInput(idea="Synthetic juice box", city="Testville", target_customer="testers")


def vprice(amount=100, unit="bottle", currency="INR", pack=None, url="https://a.test/p"):
    return Price(
        status="verified",
        amount=amount,
        currency=currency,
        unit=unit,
        pack_size=pack,
        evidence_url=url,
        accessed_on=date(2026, 1, 5),
    )


def comp(name, url=None, offer="Cold juice bottles", channels=("Website",), price=None, ev=None):
    host = name.lower().replace(" ", "")
    return Competitor(
        name=name,
        url=url or f"https://{host}.test/",
        offer=offer,
        channels=list(channels),
        price=price or Price(),
        evidence_urls=ev if ev is not None else [f"https://{host}.test/menu"],
    )


def write_run(
    runs: Path,
    run_id: str,
    comps,
    *,
    started=T0,
    state="validated_pass",
    research_input=INPUT,
    mode="sequential",
    status="complete",
) -> str:
    root = runs / run_id
    root.mkdir(parents=True)
    (root / "input.json").write_text(research_input.model_dump_json(), encoding="utf-8")
    meta = {
        "run_id": run_id,
        "mode": mode,
        "started_at": started.isoformat(),
        "finished_at": (started + timedelta(minutes=3)).isoformat(),
        "status": status,
        "acceptance": {"result": "pass", "reasons": []},
        "usage": {},
    }
    (root / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    if comps is not None:
        cs = CompetitorSet(competitors=list(comps), shortfall_reason="synthetic fixture")
        (root / "competitors.json").write_text(cs.model_dump_json(), encoding="utf-8")
    if state:
        report = ValidationReport(state=state, acceptance={"result": "pass", "reasons": []})
        (root / "validation.json").write_text(report.model_dump_json(), encoding="utf-8")
    return run_id


def pair(tmp_path, old, new, **kw_new):
    runs = tmp_path / "runs"
    a = write_run(runs, "run-a", old)
    b = write_run(
        runs, "run-b", new, started=kw_new.pop("started", T0 + timedelta(days=7)), **kw_new
    )
    return load_saved_snapshot(runs, a), load_saved_snapshot(runs, b)


def rows(result):
    return {r.name: r for r in result.rows}


# ------------------------------------------------------------------ eligibility
def test_same_scope_runs_are_compared(tmp_path):
    old, new = pair(tmp_path, [comp("Alpha")], [comp("Alpha")])
    result = compare_snapshots(old, new)
    assert result.eligible and result.idea == "Synthetic juice box"
    assert rows(result)["Alpha"].status == UNCHANGED
    assert result.baseline.run_id == "run-a" and result.latest.run_id == "run-b"


def test_scope_is_case_and_spacing_insensitive_and_ignores_known_competitors(tmp_path):
    other = INPUT.model_copy(
        update={"idea": "  synthetic JUICE   box ", "known_competitors": ["Zed"]}
    )
    old, new = pair(tmp_path, [comp("Alpha")], [comp("Alpha")], research_input=other)
    assert compare_snapshots(old, new).eligible


@pytest.mark.parametrize(
    "field,value", [("idea", "Different idea"), ("city", "Elsewhere"), ("target_customer", "pets")]
)
def test_different_scope_is_rejected_with_a_reason(tmp_path, field, value):
    other = INPUT.model_copy(update={field: value})
    old, new = pair(tmp_path, [comp("Alpha")], [comp("Alpha")], research_input=other)
    result = compare_snapshots(old, new)
    assert not result.eligible and result.rows == []
    assert any("different research scopes" in r for r in result.reasons)
    assert "Comparison unavailable" in to_markdown(result)


def test_same_run_or_older_latest_and_missing_runs_are_rejected(tmp_path):
    old, new = pair(tmp_path, [comp("Alpha")], [comp("Alpha")])
    assert not compare_snapshots(old, old).eligible
    swapped = compare_snapshots(new, old)  # baseline newer than latest
    assert not swapped.eligible and any("not older" in r for r in swapped.reasons)
    assert not compare_snapshots(None, new).eligible


def test_empty_and_incomplete_data_are_reported_not_guessed(tmp_path):
    old, new = pair(tmp_path, None, [comp("Alpha")])  # baseline has no competitors file
    result = compare_snapshots(old, new)
    assert not result.eligible and any("no competitor findings" in r for r in result.reasons)
    failed_old, failed_new = pair(tmp_path / "f", [comp("A")], [comp("A")], status="failed")
    assert any("did not finish" in r for r in compare_snapshots(failed_old, failed_new).reasons)


# ------------------------------------------------------------------ competitors
def test_new_and_absent_competitors_use_careful_labels(tmp_path):
    old, new = pair(tmp_path, [comp("Alpha"), comp("Beta")], [comp("Alpha"), comp("Gamma")])
    found = rows(compare_snapshots(old, new))
    assert found["Gamma"].status == NEW and found["Gamma"].label == "Newly observed"
    assert found["Beta"].status == NOT_OBSERVED
    assert found["Beta"].label == "Not observed in latest run"
    assert "closed" not in found["Beta"].label.lower()
    md = to_markdown(compare_snapshots(old, new))
    assert "not evidence that the business has changed or closed" in md


def test_competitors_match_by_name_or_non_generic_host_only(tmp_path):
    old, new = pair(
        tmp_path,
        [
            comp("Alpha Foods", url="https://alpha.test/", ev=["https://alpha.test/m"]),
            comp("Insta One", url="https://instagram.com/a"),
        ],
        [
            comp("Alpha Foods Pvt", url="https://alpha.test/menu", ev=["https://alpha.test/m"]),
            comp("Insta Two", url="https://instagram.com/b"),
        ],
    )
    found = rows(compare_snapshots(old, new))
    assert found["Alpha Foods Pvt"].status == UNCHANGED  # same non-generic host
    assert found["Insta Two"].status == NEW  # a shared social host alone is not a match
    assert found["Insta One"].status == NOT_OBSERVED


# ------------------------------------------------------------------ prices
def test_verified_price_change_needs_comparable_evidence_backed_amounts(tmp_path):
    old, new = pair(
        tmp_path, [comp("Alpha", price=vprice(100))], [comp("Alpha", price=vprice(120))]
    )
    row = rows(compare_snapshots(old, new))["Alpha"]
    assert row.status == CHANGED
    change = next(c for c in row.changes if c.kind == "price")
    assert change.label.startswith("Verified price change") and "+20" in change.label
    assert change.certainty == "observed" and "https://a.test/p" in change.sources


def test_equal_verified_prices_are_unchanged_and_unknown_pairs_are_silent():
    assert price_change(vprice(100), vprice(100)) is None
    assert price_change(Price(), Price()) is None


@pytest.mark.parametrize(
    "new_price",
    [vprice(120, unit="box"), vprice(120, currency="USD"), vprice(120, pack="6")],
)
def test_incomparable_prices_are_insufficient_evidence_not_a_change(new_price):
    change = price_change(vprice(100), new_price)
    assert change.label.startswith("Insufficient evidence")
    assert change.certainty == "inconclusive"


def test_verification_gained_or_lost_is_not_a_price_change(tmp_path):
    change = price_change(vprice(100), Price())
    assert change.label == "Price verification changed" and change.certainty == "inconclusive"
    assert price_change(Price(), vprice(100)).label == "Price verification changed"
    old, new = pair(tmp_path, [comp("Alpha", price=vprice(100))], [comp("Alpha")])
    row = rows(compare_snapshots(old, new))["Alpha"]
    assert row.status == REVIEW  # inconclusive only; never counted as a substantive change


def test_price_text_with_currency_symbol_variants_is_comparable():
    assert price_change(vprice(100, currency="₹"), vprice(100, currency="INR")) is None
    assert price_change(vprice(100, currency="Rs"), vprice(110, currency="inr")) is not None


# ------------------------------------------------------------------ offering, channels, evidence
def test_offering_subscription_and_channel_changes(tmp_path):
    old = comp("Alpha", offer="Cold juice. Weekly subscription box.", channels=("Website",))
    new = comp(
        "Alpha",
        offer="Cold juice and smoothies. Daily subscription plan.",
        channels=("Website", "WhatsApp"),
    )
    old_snap, new_snap = pair(tmp_path, [old], [new])
    row = rows(compare_snapshots(old_snap, new_snap))["Alpha"]
    kinds = {c.kind for c in row.changes}
    assert {"offering", "subscription", "channels"} <= kinds
    channel = next(c for c in row.changes if c.kind == "channels")
    assert "added: WhatsApp" in channel.label
    sub = next(c for c in row.changes if c.kind == "subscription")
    assert "Weekly" in sub.before and "Daily" in sub.after  # both descriptions are preserved
    off = next(c for c in row.changes if c.kind == "offering")
    assert "Cold juice." in off.before and "smoothies" in off.after
    for change in (off, sub, channel):
        assert "Research description differs — real-world change not verified" in change.label
        assert change.certainty == "inconclusive"
    assert row.status == REVIEW  # text differences are never a verified business change


def test_evidence_availability_changes_are_inconclusive_coverage_notes(tmp_path):
    old, new = pair(
        tmp_path,
        [comp("Alpha", ev=["https://alpha.test/a"])],
        [comp("Alpha", ev=["https://alpha.test/a", "https://alpha.test/b"])],
    )
    row = rows(compare_snapshots(old, new))["Alpha"]
    change = next(c for c in row.changes if c.kind == "evidence")
    assert change.certainty == "inconclusive" and "not the business" in change.label
    assert row.status == REVIEW


# ------------------------------------------------------------------ partial runs and limits
def test_partial_runs_are_compared_with_honest_limitations(tmp_path):
    old, new = pair(
        tmp_path,
        [comp("Alpha")],
        [comp("Alpha")],
        state="partial_failed_acceptance",
        mode="hierarchical",
    )
    result = compare_snapshots(old, new)
    text = " ".join(result.limitations)
    assert result.eligible
    assert "Latest run was not a fully validated report (partial_failed_acceptance)" in text
    assert "different research modes" in text
    assert "do not establish a change in the real market" in text


def test_short_gap_and_competitor_count_limits_are_stated(tmp_path):
    old, new = pair(tmp_path, [comp("A"), comp("B")], [comp("A")], started=T0 + timedelta(hours=2))
    text = " ".join(compare_snapshots(old, new).limitations)
    assert "2.0 hours apart" in text and "different number of competitors" in text


# ------------------------------------------------------------------ export
def test_markdown_export_is_deterministic_and_evidence_referenced(tmp_path):
    old, new = pair(
        tmp_path, [comp("Alpha", price=vprice(100))], [comp("Alpha", price=vprice(120)), comp("Nu")]
    )
    first = to_markdown(compare_snapshots(old, new))
    second = to_markdown(compare_snapshots(old, new))
    assert first == second
    for needle in (
        "Synthetic juice box",
        "run-a",
        "run-b",
        "2026-01-05 09:00 UTC",
        "Verified price change",
        "https://a.test/p",
        "Newly observed",
        "Comparison limitations",
        "Unverified or inconclusive observations",
    ):
        assert needle in first
    assert "datetime.now" not in first


# ------------------------------------------------------------------ zero calls
def _trap(monkeypatch):
    hits: list[str] = []

    def trap(name):
        def _fail(*a, **k):
            hits.append(name)
            raise AssertionError(name)

        return _fail

    monkeypatch.setattr("launchscout.llm.build_llm", trap("build_llm"))
    monkeypatch.setattr("crewai.LLM.call", trap("LLM.call"))
    monkeypatch.setattr("launchscout.tools._default_search", trap("serper"))
    monkeypatch.setattr("launchscout.tools._default_scrape", trap("scrape"))
    monkeypatch.setattr("launchscout.runner.run_crew", trap("crew"))
    return hits


def test_tracking_module_has_no_model_or_network_dependencies():
    code = (ROOT / "launchscout" / "tracking.py").read_text(encoding="utf-8")
    for needle in ("crewai", "openai", "requests", "httpx", "urllib", "serper", "scrape("):
        assert needle not in code


# ------------------------------------------------------------------ UI
def _tab(tmp_path, monkeypatch):
    hits = _trap(monkeypatch)
    set_manager(make_manager(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    return at, hits


def test_ui_empty_state_with_no_or_one_saved_run(tmp_path, monkeypatch):
    at, hits = _tab(tmp_path, monkeypatch)
    text = " ".join(m.value for m in at.tabs[2].markdown)
    assert "Not enough saved runs" in text and "Need two saved runs" in text
    write_run(tmp_path / "runs", "run-a", [comp("Alpha")])
    set_manager(make_manager(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert "Need two saved runs" in " ".join(m.value for m in at.tabs[2].markdown)
    assert hits == [] and not at.exception


def test_ui_shows_comparison_kpis_table_and_keeps_scheduler_truthful(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    write_run(runs, "run-a", [comp("Alpha", price=vprice(100)), comp("Beta")])
    write_run(
        runs,
        "run-b",
        [comp("Alpha", price=vprice(120)), comp("Gamma")],
        started=T0 + timedelta(days=7),
    )
    at, hits = _tab(tmp_path, monkeypatch)
    tab = at.tabs[2]
    assert tab.selectbox(key="track_latest").value == "run-b"
    assert tab.selectbox(key="track_baseline").value == "run-a"
    text = " ".join(m.value for m in tab.markdown)
    assert "Comparison available" in text
    assert "Confirmed configured: no" in text and "none recorded" in text
    values = tracking_values(tab.markdown)
    assert values["Newly observed"] == "1" and values["Not observed in latest run"] == "1"
    assert values["Changed (verified)"] == "1" and values["Verified changes"] == "1"
    assert values["Saved research runs"] == "2" and values["Monitoring status"] == "Manual"
    assert tab.button(key="weekly_rerun").disabled is True  # Rerun now stays disabled
    assert not at.exception and hits == []


def test_ui_incompatible_selection_shows_reason(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    write_run(runs, "run-a", [comp("Alpha")])
    write_run(
        runs,
        "run-b",
        [comp("Alpha")],
        started=T0 + timedelta(days=1),
        research_input=INPUT.model_copy(update={"city": "Elsewhere"}),
    )
    at, hits = _tab(tmp_path, monkeypatch)
    text = " ".join(m.value for m in at.tabs[2].markdown)
    assert "Comparison unavailable" in text
    assert any("different research scopes" in w.value for w in at.tabs[2].warning)
    assert hits == []


# ------------------------------------------------------------------ classification correction
def test_wording_differences_never_count_as_changed_in_kpis(tmp_path):
    old = comp("Alpha", offer="Cold juice. Weekly subscription.", channels=("Website",))
    new = comp("Alpha", offer="Juices and shots. Daily plan.", channels=("Website", "Instagram"))
    old_snap, new_snap = pair(tmp_path, [old], [new])
    result = compare_snapshots(old_snap, new_snap)
    assert result.count(CHANGED) == 0 and result.count(REVIEW) == 1
    md = to_markdown(result)
    assert "- Changed: 0" in md and "Research description differs" in md


def test_verified_price_difference_still_counts_as_changed_with_wording_noise(tmp_path):
    old = comp("Alpha", offer="Cold juice", price=vprice(100))
    new = comp("Alpha", offer="Cold juice, reworded", price=vprice(130))
    old_snap, new_snap = pair(tmp_path, [old], [new])
    result = compare_snapshots(old_snap, new_snap)
    assert result.count(CHANGED) == 1
    kinds = {c.kind: c.certainty for c in result.rows[0].changes}
    assert kinds["price"] == "observed" and kinds["offering"] == "inconclusive"


@pytest.mark.skipif(
    not (any(ROOT.glob("runs/*3824")) and any(ROOT.glob("runs/*c0fe"))),
    reason="saved L5/L6 runs are not present on this machine",
)
def test_real_l5_vs_l6_wording_differences_are_not_verified_changes():
    runs = ROOT / "runs"
    l5 = load_saved_snapshot(runs, next(runs.glob("*3824")).name)
    l6 = load_saved_snapshot(runs, next(runs.glob("*c0fe")).name)
    result = compare_snapshots(l5, l6)
    assert result.eligible
    assert result.count(CHANGED) == 0 and result.count(NEW) == 0
    assert result.count(NOT_OBSERVED) == 0
    assert all(r.status in (REVIEW, UNCHANGED) for r in result.rows)
    assert all(c.certainty == "inconclusive" for r in result.rows for c in r.changes)
    assert any("different research modes" in t for t in result.limitations)


def test_ui_changed_kpi_excludes_text_differences(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    write_run(runs, "run-a", [comp("Alpha", offer="Cold juice")])
    write_run(
        runs, "run-b", [comp("Alpha", offer="Different wording")], started=T0 + timedelta(days=7)
    )
    at, hits = _tab(tmp_path, monkeypatch)
    values = tracking_values(at.tabs[2].markdown)
    assert values["Verified changes"] == "0" and values["Needs review"] == "1"
    assert values["Changed (verified)"] == "0"
    assert hits == []
