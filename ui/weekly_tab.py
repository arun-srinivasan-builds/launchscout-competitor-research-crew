"""Weekly Tracking tab. Informative placeholders only; behaviour arrives in M7."""

from __future__ import annotations

import streamlit as st

from ui.theme import pill, section


def render() -> None:
    section(
        "Weekly competitor tracking",
        "Save a research configuration, rerun it weekly and highlight price changes. "
        "Not yet implemented (M7): no configurations, snapshots or price comparisons exist.",
    )
    st.markdown(
        '<div class="ls-card"><h4>Scheduler status</h4>'
        '<div class="ls-row ls-muted">Three separate facts, never inferred from one another.</div>'
        f'<div class="ls-row">{pill("Documented: not yet written", "warn")}'
        f"{pill('Confirmed configured: no', 'warn')}"
        f"{pill('Last successful scheduled run: none recorded', 'idle')}</div></div>",
        unsafe_allow_html=True,
    )
    st.button("Rerun now", disabled=True, key="weekly_rerun")
