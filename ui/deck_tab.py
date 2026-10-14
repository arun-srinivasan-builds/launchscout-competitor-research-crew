"""Pitch Deck tab. Disabled until a validated report exists (deck generation arrives in M6)."""

from __future__ import annotations

import streamlit as st

from ui.theme import pill, section


def render() -> None:
    section(
        "Six-slide pitch deck",
        "An editable PowerPoint generated only from a report that passed acceptance validation.",
    )
    st.markdown(
        '<div class="ls-card"><h4>Status</h4>'
        f"{pill('No validated report', 'warn')}"
        f"{pill('Generation not yet implemented (M6)', 'idle')}"
        '<div class="ls-row ls-muted">The six slides will be: Idea &amp; Market, Competitor '
        "Landscape, Customer Pain Points, Market Gap, Positioning &amp; Price, 30-Day Launch "
        "Plan. A partial or failed-acceptance report cannot produce a validated deck.</div></div>",
        unsafe_allow_html=True,
    )
    st.button("Generate pitch deck", disabled=True, key="deck_generate")
