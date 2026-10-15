"""Weekly Tracking tab: offline competitor change dashboard over saved research runs.

Change tracking compares two *saved* research runs deterministically. It never starts research,
calls a model, searches or scrapes; scheduled weekly reruns remain a separate, unimplemented
feature and are described as such. Every figure shown comes from the comparison or the saved-run
list; the visual layer (`ui/tracking_view.py`) adds no statistics of its own.
"""

from __future__ import annotations

from collections import Counter

import streamlit as st

from launchscout.runner import get_manager
from launchscout.saved_runs import SavedRunSummary, list_saved_runs, load_saved_snapshot
from launchscout.tracking import (
    Comparison,
    check_compatibility,
    compare_snapshots,
    to_markdown,
)
from ui import tracking_view as view
from ui.theme import inject_tracking_theme, pill

BASELINE_KEY = "track_baseline"
LATEST_KEY = "track_latest"
COMPARABLE_LABELS = ("validated", "partial", "legacy")


def _candidates() -> tuple[list[SavedRunSummary], str]:
    manager = get_manager()
    runs = [r for r in list_saved_runs(manager.runs_dir()) if r.label in COMPARABLE_LABELS]
    return runs, str(manager.runs_dir())


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def _title(text: str) -> None:
    _html(f'<div class="tk-section-title">{text}</div>')


def _scheduler_panel() -> None:
    """Three separate scheduler facts (never inferred from one another) and the disabled rerun."""
    _title("Monitoring status")
    _html(
        '<div class="tk-panel"><h4>Scheduler status</h4>'
        '<div class="tk-muted">Weekly monitoring is manual. Scheduled reruns are not '
        "implemented; this dashboard compares runs that were already saved.</div>"
        f"{pill('Documented: not yet written', 'warn')}"
        f"{pill('Confirmed configured: no', 'warn')}"
        f"{pill('Last successful scheduled run: none recorded', 'idle')}</div>"
    )
    st.button("Rerun now", disabled=True, key="weekly_rerun")


def _render_comparison(result: Comparison) -> None:
    ok = result.eligible
    chips = pill("Comparison available" if ok else "Comparison unavailable", "ok" if ok else "warn")
    note = (
        "Both runs finished, cover the same idea and market, and the baseline is older."
        if ok
        else "These runs cannot be compared; see the reasons below."
    )
    _html(
        '<div class="tk-elig"><span class="tk-elig-label">Eligibility</span>'
        f'{chips}<span class="tk-elig-note">{note}</span></div>'
    )
    if not ok:
        for reason in result.reasons:
            st.warning(reason)
        return
    _html(view.run_cards_html(result))
    _title("Change verification")
    _html(view.verification_html(result))
    _title("Competitor changes")
    if result.rows:
        _html(view.table_html(result))
    else:
        st.info("Neither run recorded any competitors.")
    for row in result.rows:
        if not (row.changes or row.baseline_sources or row.latest_sources):
            continue
        with st.expander(f"{row.name}: {row.label}"):
            _html(view.detail_html(row))
    with st.expander("Comparison limitations", expanded=True):
        _html(view.limitations_html(result.limitations))
    st.download_button(
        "Download change summary (Markdown)",
        data=to_markdown(result),
        file_name=f"competitor-changes-{result.baseline.run_id}-vs-{result.latest.run_id}.md"
        if result.baseline and result.latest
        else "competitor-changes.md",
        mime="text/markdown",
        key="track_download",
    )


def _empty_state() -> None:
    _html(
        '<div class="ls-card"><h4>Not enough saved runs</h4>'
        f'<div class="ls-row">{pill("Need two saved runs", "warn")}</div>'
        '<div class="ls-row ls-muted">Change tracking needs two saved research runs of the '
        "same business idea and market. Run the research again later (it is never started "
        "from this tab) and return to compare the snapshots.</div></div>"
    )


def _select_and_compare(runs: list[SavedRunSummary]) -> Comparison:
    by_id = {r.run_id: r for r in runs}
    ids = list(by_id)
    manager = get_manager()
    left, right = st.columns(2)
    with left:
        latest_id = st.selectbox(
            "Latest run", ids, index=0, format_func=lambda i: by_id[i].title, key=LATEST_KEY
        )
    latest = load_saved_snapshot(manager.runs_dir(), latest_id)
    # default baseline: the newest older run with the same scope, else the next run
    default = 1
    for position, run_id in enumerate(ids):
        if run_id == latest_id:
            continue
        candidate = load_saved_snapshot(manager.runs_dir(), run_id)
        if not check_compatibility(candidate, latest):
            default = position
            break
    with right:
        baseline_id = st.selectbox(
            "Baseline run",
            ids,
            index=min(default, len(ids) - 1),
            format_func=lambda i: by_id[i].title,
            key=BASELINE_KEY,
        )
    baseline = load_saved_snapshot(manager.runs_dir(), baseline_id)
    return compare_snapshots(baseline, latest)


def render() -> None:
    inject_tracking_theme()
    _html(view.header_html())
    runs, _ = _candidates()
    counts = Counter(r.label for r in runs)
    run_counts = {name: counts.get(name, 0) for name in COMPARABLE_LABELS}
    kpi_slot = st.container()
    result: Comparison | None = None
    _title("Compare saved research runs")
    st.caption(
        "Compare two saved runs of the same idea. Deterministic and offline: no model calls, "
        "searches or new research. Wording differences are never reported as verified changes."
    )
    if len(runs) < 2:
        _empty_state()
    else:
        result = _select_and_compare(runs)
    with kpi_slot:
        _html(view.kpi_html(result, run_counts))
    if result is not None:
        _render_comparison(result)
    _scheduler_panel()
