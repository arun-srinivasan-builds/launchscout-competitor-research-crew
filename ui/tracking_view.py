"""Weekly Tracking dashboard components: pure HTML builders over a `Comparison`.

Every number and sentence comes from the comparison (or from the saved-run list) passed in.
Nothing here computes a trend, scores a change or reads anything else. All text is escaped and
there are no inline styles: classes (CSS lives in `ui/theme.py`) and `<progress>` elements
carry the geometry.
"""

from __future__ import annotations

from html import escape

from launchscout.tracking import (
    CHANGED,
    NEW,
    NOT_OBSERVED,
    REVIEW,
    STATUS_ORDER,
    UNCHANGED,
    Change,
    Comparison,
    CompetitorChange,
    SnapshotInfo,
)

EM_DASH = "—"

# Short badge text per status; the full explanation lives in the detail panel.
BADGE = {
    NEW: "Newly observed",
    NOT_OBSERVED: "Not observed in latest run",
    CHANGED: "Changed (verified)",
    REVIEW: "Needs review",
    UNCHANGED: "No change observed",
}
CSS_CLASS = {NEW: "tk-new", NOT_OBSERVED: "tk-gone", CHANGED: "tk-chg", REVIEW: "tk-rev",
             UNCHANGED: "tk-same"}
# Why a classification was (or was not) verified: the rules in `launchscout.tracking`.
WHY = {
    CHANGED: "Verified: both runs carry a complete, evidence-backed price with the same "
    "currency, unit and pack size, and the amounts differ.",
    REVIEW: "Not verified: the research descriptions differ (wording, offering, subscription "
    "or channels). Two research runs can word the same business differently, so the "
    "real-world change is unconfirmed.",
    NEW: "Observed in the latest run only. This does not show that the business is new.",
    NOT_OBSERVED: "Found in the baseline run but not in the latest. This is not evidence that "
    "the business changed or closed.",
    UNCHANGED: "No difference found in the compared fields.",
}
KIND_TEXT = {
    "offering": "Offering description differs",
    "subscription": "Subscription description differs",
    "channels": "Sales channels differ",
    "evidence": "Evidence availability differs",
}
FLOOR_NOTE = "Counts of competitors in this one comparison. Not a trend and not a score."


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def safe_url(url: str) -> str | None:
    """Return the URL only if it is plain http(s); anything else is shown as text, not linked."""
    return url if url.lower().startswith(("http://", "https://")) else None


def link(url: str) -> str:
    target = safe_url(url)
    if target is None:
        return f'<span class="tk-url">{_e(url)}</span>'
    return (
        f'<a class="tk-url" href="{_e(target)}" target="_blank" '
        f'rel="noopener noreferrer">{_e(url)}</a>'
    )


# ------------------------------------------------------------------ header
def header_html() -> str:
    return (
        '<div class="tk-hero">'
        '<div class="tk-hero-text"><div class="tk-eyebrow">Market intelligence</div>'
        "<h2>Weekly Tracking</h2>"
        '<div class="tk-sub">What changed between two saved research runs of the same '
        "idea, with the evidence behind every finding.</div></div>"
        '<div class="tk-hero-chips">'
        '<span class="tk-chip tk-chip-gold">MANUAL &middot; OFFLINE</span>'
        '<span class="tk-chip">Saved-run comparison</span>'
        '<span class="tk-chip">No model or search calls</span></div></div>'
    )


# ------------------------------------------------------------------ KPI cards
def _svg(paths: str) -> str:
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + paths + "</svg>"
    )


KPI_ICON = {
    "verified": _svg(
        '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/>'
    ),
    "review": _svg('<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>'
                   '<circle cx="12" cy="12" r="2.8"/>'),
    "runs": _svg('<path d="M12 3l9 4.5-9 4.5-9-4.5z"/><path d="M3 12l9 4.5 9-4.5"/>'
                 '<path d="M3 16.5L12 21l9-4.5"/>'),
    "monitoring": _svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
}


def _kpi(key: str, label: str, value: str, note: str, tone: str) -> str:
    return (
        f'<div class="tk-kpi tk-kpi-{tone}" data-kpi="{_e(key)}">'
        f'<span class="tk-kpi-icon">{KPI_ICON[key]}</span>'
        '<div class="tk-kpi-body">'
        f'<div class="tk-kpi-label">{_e(label)}</div>'
        f'<div class="tk-kpi-val" data-value="{_e(value)}">{_e(value)}</div>'
        f'<div class="tk-kpi-note">{_e(note)}</div></div></div>'
    )


def kpi_html(result: Comparison | None, run_counts: dict[str, int]) -> str:
    """Four KPI cards. Comparison-dependent values are an em dash until one is available."""
    ok = result is not None and result.eligible
    verified = str(result.count(CHANGED)) if ok and result else EM_DASH
    review = str(result.count(REVIEW)) if ok and result else EM_DASH
    total = sum(run_counts.values())
    parts = [f"{n} {name}" for name, n in run_counts.items() if n]
    return (
        '<div class="tk-kpis">'
        + _kpi(
            "verified", "Verified changes", verified,
            "Comparable, evidence-backed price differences", "teal",
        )
        + _kpi(
            "review", "Needs review", review,
            "Descriptions differ; real-world change not verified", "gold",
        )
        + _kpi(
            "runs", "Saved research runs", str(total),
            " · ".join(parts) if parts else "None saved yet", "blue",
        )
        + _kpi(
            "monitoring", "Monitoring status", "Manual", "Offline comparison; no scheduler", "navy"
        )
        + "</div>"
    )


# ------------------------------------------------------------------ run comparison cards
def _run_card(role: str, info: SnapshotInfo) -> str:
    state = (info.report_state or "not recorded").replace("_", " ")
    model = info.model_name or "not recorded"
    started = info.started_at.strftime("%Y-%m-%d %H:%M UTC")
    rows = (
        ("Started", started),
        ("Report state", state),
        ("Research mode", info.mode),
        ("Model", model),
        ("Competitors found", str(info.competitor_count)),
        ("Verified prices", str(info.verified_prices)),
    )
    body = "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in rows)
    return (
        f'<div class="tk-run"><div class="tk-run-role">{_e(role)}</div>'
        f'<div class="tk-run-id">{_e(info.run_id)}</div><dl>{body}</dl></div>'
    )


def run_cards_html(result: Comparison) -> str:
    if not result.eligible or result.baseline is None or result.latest is None:
        return ""
    scope = f"{_e(result.idea)} &middot; {_e(result.city)}"
    return (
        '<div class="tk-runs">'
        + _run_card("Baseline run", result.baseline)
        + '<div class="tk-run-mid"><span class="tk-vs" aria-hidden="true">VS</span></div>'
        + _run_card("Latest run", result.latest)
        + f'</div><div class="tk-scope">Same scope: {scope}</div>'
    )


# ------------------------------------------------------------------ verification section
def _source_count(row: CompetitorChange) -> int:
    return len(set(row.latest_sources) | set(row.baseline_sources))


def verification_html(result: Comparison) -> str:
    """Status distribution and evidence coverage: counts in this comparison only."""
    if not result.eligible:
        return ""
    total = len(result.rows)
    dist = []
    for status in STATUS_ORDER:
        n = result.count(status)
        dist.append(
            f'<div class="tk-dist-row {CSS_CLASS[status]}">'
            f'<span class="tk-dist-label">{_e(BADGE[status])}</span>'
            f'<progress value="{n}" max="{max(total, 1)}" aria-label="{_e(BADGE[status])}">'
            f"{n}</progress>"
            f'<span class="tk-dist-n">{n} of {total}</span></div>'
        )
    cover = []
    peak = max((max(len(r.baseline_sources), len(r.latest_sources)) for r in result.rows),
               default=0)
    for row in result.rows:
        for role, urls in (("Baseline", row.baseline_sources), ("Latest", row.latest_sources)):
            cover.append(
                '<div class="tk-cov-row">'
                f'<span class="tk-cov-name">{_e(row.name)} <small>{role}</small></span>'
                f'<progress value="{len(urls)}" max="{max(peak, 1)}" '
                f'aria-label="{_e(row.name)} {role} evidence URLs">{len(urls)}</progress>'
                f'<span class="tk-dist-n">{len(urls)}</span></div>'
            )
    coverage = (
        '<div class="tk-panel"><h4>Evidence coverage</h4>'
        '<div class="tk-muted">Evidence URLs cited per competitor in each run.</div>'
        + "".join(cover) + "</div>"
        if cover
        else ""
    )
    return (
        '<div class="tk-split">'
        '<div class="tk-panel"><h4>Status distribution</h4>'
        f'<div class="tk-muted">{_e(FLOOR_NOTE)}</div>' + "".join(dist) + "</div>"
        + coverage + "</div>"
    )


# ------------------------------------------------------------------ table
def _short_detail(row: CompetitorChange) -> str:
    """One compact line for the table; the full labels and quotes are in the detail panel."""
    parts: list[str] = []
    for change in row.changes:
        text = change.label if change.kind == "price" else KIND_TEXT.get(change.kind, change.label)
        if text not in parts:
            parts.append(text)
    if parts:
        return "; ".join(parts)
    return "No difference found in the compared fields" if row.status == UNCHANGED else EM_DASH


def table_html(result: Comparison) -> str:
    if not result.eligible or not result.rows:
        return ""
    body = []
    for r in result.rows:
        detail = _short_detail(r)
        cls = CSS_CLASS.get(r.status, "tk-same")
        body.append(
            f'<tr class="{cls}">'
            f'<td data-label="Competitor"><strong>{_e(r.name)}</strong></td>'
            f'<td data-label="Status"><span class="tk-badge {cls}">'
            f"{_e(BADGE.get(r.status, r.label))}</span></td>"
            f'<td data-label="Detail">{_e(detail)}</td>'
            f'<td data-label="Evidence URLs">{_source_count(r)}</td>'
            f'<td data-label="Baseline / latest">{len(r.baseline_sources)} / '
            f"{len(r.latest_sources)}</td></tr>"
        )
    return (
        '<div class="tk-table-wrap"><table class="tk-table"><thead><tr>'
        "<th>Competitor</th><th>Status</th><th>Detail</th><th>Evidence URLs</th>"
        "<th>Baseline / latest</th></tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
    )


# ------------------------------------------------------------------ evidence detail
def _change_html(change: Change) -> str:
    observed = change.certainty == "observed"
    tone = "tk-chg" if observed else "tk-rev"
    cert = "Observed" if observed else "Inconclusive"
    sides = ""
    if change.before or change.after:
        sides = (
            '<div class="tk-sides"><div><div class="tk-side-role">Baseline</div>'
            f"{_e(change.before) or EM_DASH}</div>"
            f'<div><div class="tk-side-role">Latest</div>{_e(change.after) or EM_DASH}</div></div>'
        )
    srcs = "".join(f"<li>{link(u)}</li>" for u in change.sources)
    src_html = f'<ul class="tk-urls">{srcs}</ul>' if srcs else ""
    return (
        f'<div class="tk-change"><div class="tk-change-top"><strong>{_e(change.label)}</strong>'
        f'<span class="tk-badge {tone}">{cert}</span></div>{sides}{src_html}</div>'
    )


def detail_html(row: CompetitorChange) -> str:
    """Why this row was (or was not) verified, the differences, and the cited evidence."""
    cls = CSS_CLASS.get(row.status, "tk-same")
    parts = [
        f'<div class="tk-why {cls}"><strong>{_e(BADGE.get(row.status, row.label))}.</strong> '
        f"{_e(WHY.get(row.status, row.label))}</div>"
    ]
    parts += [_change_html(c) for c in row.changes]
    if not row.changes:
        urls = row.latest_sources or row.baseline_sources
        if urls:
            parts.append(
                '<div class="tk-change"><strong>Evidence</strong><ul class="tk-urls">'
                + "".join(f"<li>{link(u)}</li>" for u in urls)
                + "</ul></div>"
            )
    return "".join(parts)


def limitations_html(items: list[str]) -> str:
    return '<ul class="tk-limits">' + "".join(f"<li>{_e(t)}</li>" for t in items) + "</ul>"


def dashboard_html(result: Comparison) -> str:
    """Run comparison (left) and change verification overview (right) on wide screens.

    The two sections stack in this order on narrower screens (CSS only).
    """
    if not result.eligible:
        return ""
    return (
        '<div class="tk-dash">'
        '<section class="tk-col"><div class="tk-section-title">Run comparison</div>'
        + run_cards_html(result)
        + '</section><section class="tk-col"><div class="tk-section-title">'
        "Change verification overview</div>"
        + verification_html(result)
        + "</section></div>"
    )
