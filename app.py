"""LaunchScout Streamlit entry point: exactly three tabs."""

from __future__ import annotations

import streamlit as st

from ui import deck_tab, research_tab, weekly_tab
from ui.theme import TAB_LABELS, hero, inject_theme


def main() -> None:
    st.set_page_config(page_title="LaunchScout", page_icon=None, layout="wide")
    inject_theme()
    hero(
        "LaunchScout",
        "Sourced competitor research for a new business idea: competitors, prices, "
        "customer complaints, market gap and a 30-day launch plan.",
    )
    research, deck, weekly = st.tabs(list(TAB_LABELS))
    with research:
        research_tab.render()
    with deck:
        deck_tab.render()
    with weekly:
        weekly_tab.render()


main()
