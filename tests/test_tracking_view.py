"""Weekly Tracking dashboard components: honest, escaped, derived only from the comparison."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from launchscout.tracking import (
    CHANGED,
    NEW,
    NOT_OBSERVED,
    REVIEW,
    UNCHANGED,
    Change,
    Comparison,
    CompetitorChange,
    SnapshotInfo,
)
from ui import tracking_view as view

ROOT = Path(__file__).resolve().parent.parent
T0 = datetime(2026, 10, 1, 9, 30, tzinfo=UTC)


def info(run_id: str, n: int = 2, prices: int = 1) -> SnapshotInfo:
    return SnapshotInfo(
        run_id=run_id,
        started_at=T0,
        report_state="partial",
        mode="sequential",
        model_name="model-x",
        competitor_count=n,
        verified_prices=prices,
    )


def row(name: str, status: str, **kw) -> CompetitorChange:
    return CompetitorChange(name=name, status=status, label=view.BADGE[status], **kw)


def comparison(rows: list[CompetitorChange], eligible: bool = True) -> Comparison:
    return Comparison(
        eligible=eligible,
        reasons=[] if eligible else ["different research scopes"],
        idea="Juice <b>box</b>",
        city="Pune",
        baseline=info("run-a") if eligible else None,
        latest=info("run-b") if eligible else None,
        rows=rows,
        limitations=["Runs used different modes <script>"],
    )


def test_header_states_manual_offline_and_makes_no_scheduler_claim():
    html = view.header_html()
    assert "MANUAL" in html and "OFFLINE" in html and "Saved-run comparison" in html
    assert "ls-logo-tile" not in html  # the main app header already carries the logo
    assert "scheduled" not in html.lower() and "automatic" not in html.lower()


def test_kpis_come_from_the_comparison_and_are_dashes_without_one():
    result = comparison([row("A", CHANGED), row("B", REVIEW), row("C", REVIEW), row("D", NEW)])
    html = view.kpi_html(result, {"validated": 1, "partial": 2, "legacy": 0})
    assert 'data-kpi="verified"' in html and 'data-value="1"' in html
    assert re.search(r'data-kpi="review".*?data-value="2"', html, re.S)
    assert re.search(r'data-kpi="runs".*?data-value="3"', html, re.S)
    assert "1 validated" in html and "2 partial" in html and "legacy" not in html
    assert re.search(r'data-kpi="monitoring".*?data-value="Manual"', html, re.S)
    empty = view.kpi_html(None, {"validated": 0, "partial": 1, "legacy": 0})
    assert empty.count('data-value="—"') == 2
    ineligible = view.kpi_html(comparison([], eligible=False), {"validated": 0})
    assert ineligible.count('data-value="—"') == 2


def test_wording_differences_are_needs_review_never_verified():
    result = comparison(
        [
            row(
                "Alpha",
                REVIEW,
                changes=[
                    Change(
                        kind="offering", label="Research description differs",
                        before="Cold juice", after="Juices and shots", certainty="inconclusive",
                    )
                ],
            )
        ]
    )
    table = view.table_html(result)
    assert "Needs review" in table and "Changed (verified)" not in table
    detail = view.detail_html(result.rows[0])
    assert "Not verified" in detail and "Inconclusive" in detail
    assert "Verified:" not in detail
    kpi = view.kpi_html(result, {"validated": 2})
    assert re.search(r'data-kpi="verified".*?data-value="0"', kpi, re.S)


def test_verified_row_explains_the_rule_and_not_observed_is_not_closure():
    changed = row(
        "Alpha",
        CHANGED,
        changes=[Change(kind="price", label="Price changed", before="100", after="120")],
    )
    assert "evidence-backed price" in view.detail_html(changed)
    gone = view.detail_html(row("Beta", NOT_OBSERVED, baseline_sources=["https://b.example"]))
    assert "not evidence that the business changed or closed" in gone


def test_distribution_counts_match_rows_and_sum_to_the_total():
    rows = [row("A", NEW), row("B", NEW), row("C", UNCHANGED), row("D", NOT_OBSERVED)]
    html = view.verification_html(comparison(rows))
    assert 'value="2" max="4" aria-label="Newly observed"' in html
    assert 'value="1" max="4" aria-label="No change observed"' in html
    assert "Not a trend" in html
    assert view.verification_html(comparison([], eligible=False)) == ""


def test_evidence_coverage_uses_real_url_counts():
    rows = [row("A", REVIEW, baseline_sources=["https://a/1"], latest_sources=["https://a/1", "https://a/2"])]
    html = view.verification_html(comparison(rows))
    assert 'value="1" max="2" aria-label="A Baseline evidence URLs"' in html
    assert 'value="2" max="2" aria-label="A Latest evidence URLs"' in html


def test_untrusted_text_is_escaped_and_non_http_urls_are_not_linked():
    r = row(
        "<img src=x onerror=1>",
        REVIEW,
        changes=[
            Change(
                kind="offering", label="<b>x</b>", before="<script>1</script>", after="ok",
                sources=["javascript:alert(1)", "https://good.example/p?a=1&b=2"],
            )
        ],
    )
    html = view.table_html(comparison([r])) + view.detail_html(r)
    assert "<img" not in html and "<script>" not in html and "<b>x</b>" not in html
    assert 'href="javascript:' not in html
    assert 'href="https://good.example/p?a=1&amp;b=2"' in html and "noopener noreferrer" in html
    assert "Juice <b>box</b>" not in view.run_cards_html(comparison([]))
    assert "<script>" not in view.limitations_html(comparison([]).limitations)


def test_run_cards_show_both_runs_source_facts_and_ineligible_has_none():
    html = view.run_cards_html(comparison([]))
    wanted = ("Baseline run", "Latest run", "run-a", "run-b", "model-x", "partial", "sequential")
    for text in wanted:
        assert text in html
    assert view.run_cards_html(comparison([], eligible=False)) == ""


def test_dashboard_markup_has_no_inline_styles():
    result = comparison(
        [row("A", CHANGED, latest_sources=["https://a/1"]), row("B", REVIEW)]
    )
    blob = (
        view.header_html()
        + view.kpi_html(result, {"validated": 1})
        + view.run_cards_html(result)
        + view.verification_html(result)
        + view.table_html(result)
        + view.detail_html(result.rows[0])
    )
    assert "style=" not in blob
    source = (ROOT / "ui" / "tracking_view.py").read_text(encoding="utf-8")
    assert "style=" not in source
