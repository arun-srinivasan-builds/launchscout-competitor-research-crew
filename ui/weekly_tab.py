"""Weekly Tracking tab: scheduler status (not implemented) and offline competitor change tracking.

Change tracking compares two *saved* research runs deterministically. It never starts research,
calls a model, searches or scrapes; scheduled reruns remain a separate, unimplemented feature.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from launchscout.runner import get_manager
from launchscout.saved_runs import SavedRunSummary, list_saved_runs, load_saved_snapshot
from launchscout.tracking import (
    CHANGED,
    NEW,
    NOT_OBSERVED,
    REVIEW,
    Comparison,
    check_compatibility,
    compare_snapshots,
    to_markdown,
)
from ui.theme import pill, section

BASELINE_KEY = "track_baseline"
LATEST_KEY = "track_latest"
COMPARABLE_LABELS = ("validated", "partial", "legacy")


def _scheduler_card() -> None:
    st.markdown(
        '<div class="ls-card"><h4>Scheduler status</h4>'
        '<div class="ls-row ls-muted">Three separate facts, never inferred from one another.</div>'
        f'<div class="ls-row">{pill("Documented: not yet written", "warn")}'
        f"{pill('Confirmed configured: no', 'warn')}"
        f"{pill('Last successful scheduled run: none recorded', 'idle')}</div></div>",
        unsafe_allow_html=True,
    )
    st.button("Rerun now", disabled=True, key="weekly_rerun")


def _candidates() -> tuple[list[SavedRunSummary], str]:
    manager = get_manager()
    runs = [r for r in list_saved_runs(manager.runs_dir()) if r.label in COMPARABLE_LABELS]
    return runs, str(manager.runs_dir())


def _render_comparison(result: Comparison) -> None:
    ok = result.eligible
    chips = pill("Comparison available" if ok else "Comparison unavailable", "ok" if ok else "warn")
    st.markdown(f'<div class="ls-card"><h4>Eligibility</h4>{chips}</div>', unsafe_allow_html=True)
    if not ok:
        for reason in result.reasons:
            st.warning(reason)
        return
    cols = st.columns(4)
    cols[0].metric("Newly observed", result.count(NEW))
    cols[1].metric("Not observed in latest run", result.count(NOT_OBSERVED))
    cols[2].metric("Changed", result.count(CHANGED))
    cols[3].metric("Needs review", result.count(REVIEW))
    rows = [
        {
            "Competitor": r.name,
            "Status": r.label,
            "Detail": "; ".join(c.label for c in r.changes)
            or ("No difference found in the compared fields" if r.status == "unchanged" else ""),
            "Evidence URLs": len(set(r.latest_sources) | set(r.baseline_sources)),
        }
        for r in result.rows
    ]
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info("Neither run recorded any competitors.")
    for row in result.rows:
        if not (row.changes or row.baseline_sources or row.latest_sources):
            continue
        with st.expander(f"{row.name}: {row.label}"):
            for change in row.changes:
                certainty = "observed" if change.certainty == "observed" else "inconclusive"
                st.markdown(f"**{escape(change.label)}** ({certainty})")
                if change.before or change.after:
                    st.markdown(
                        f"- Baseline: {escape(change.before)}\n- Latest: {escape(change.after)}"
                    )
                for url in change.sources:
                    st.markdown(f"- Source: {url}")
            if row.status == NOT_OBSERVED:
                st.caption(
                    "Not found in the latest research. This is not evidence that the business "
                    "changed or closed."
                )
            if not row.changes:
                for url in row.latest_sources or row.baseline_sources:
                    st.markdown(f"- Evidence: {url}")
    with st.expander("Comparison limitations", expanded=True):
        for text in result.limitations:
            st.markdown(f"- {escape(text)}")
    st.download_button(
        "Download change summary (Markdown)",
        data=to_markdown(result),
        file_name=f"competitor-changes-{result.baseline.run_id}-vs-{result.latest.run_id}.md"
        if result.baseline and result.latest
        else "competitor-changes.md",
        mime="text/markdown",
        key="track_download",
    )


def _render_tracking() -> None:
    section(
        "Competitor change tracking",
        "Compare two saved research runs of the same idea. Deterministic and offline: no model "
        "calls, searches or new research.",
    )
    runs, _ = _candidates()
    if len(runs) < 2:
        st.markdown(
            '<div class="ls-card"><h4>Not enough saved runs</h4>'
            f'<div class="ls-row">{pill("Need two saved runs", "warn")}</div>'
            '<div class="ls-row ls-muted">Change tracking needs two saved research runs of the '
            "same business idea and market. Run the research again later (it is never started "
            "from this tab) and return to compare the snapshots.</div></div>",
            unsafe_allow_html=True,
        )
        return
    by_id = {r.run_id: r for r in runs}
    ids = list(by_id)
    latest_id = st.selectbox(
        "Latest run", ids, index=0, format_func=lambda i: by_id[i].title, key=LATEST_KEY
    )
    manager = get_manager()
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
    baseline_id = st.selectbox(
        "Baseline run",
        ids,
        index=min(default, len(ids) - 1),
        format_func=lambda i: by_id[i].title,
        key=BASELINE_KEY,
    )
    baseline = load_saved_snapshot(manager.runs_dir(), baseline_id)
    _render_comparison(compare_snapshots(baseline, latest))


def render() -> None:
    section(
        "Weekly competitor tracking",
        "Scheduled weekly reruns are not implemented. Change tracking below compares saved "
        "research runs and makes no calls.",
    )
    _scheduler_card()
    _render_tracking()
