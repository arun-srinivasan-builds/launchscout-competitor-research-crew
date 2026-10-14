"""LaunchScout Streamlit entry point: exactly three tabs."""

from __future__ import annotations

import streamlit as st

from ui import deck_tab, research_tab, weekly_tab
from ui.chrome import inject_back_to_top
from ui.theme import TAB_LABELS, hero, inject_theme


def main() -> None:
    st.set_page_config(page_title="LaunchScout", page_icon=None, layout="wide")
    inject_theme()
    inject_back_to_top()
    hero("LaunchScout", "Competitor Research Crew", "From market intelligence to launch strategy.")
    research, deck, weekly = st.tabs(list(TAB_LABELS))
    with research:
        research_tab.render()
    with deck:
        deck_tab.render()
    with weekly:
        weekly_tab.render()


main()
