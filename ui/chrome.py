"""Application chrome: brand logo reference and the floating Back to top control.

Both are presentation only. They make no model, search or research call, and they never
touch session state or trigger a Streamlit rerun.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"
STATIC = Path(__file__).resolve().parent.parent / "static"
ORIGINAL_LOGO_FILE = STATIC / "ls_logo.png"  # supplied artwork, kept for comparison
LOGO_FILE = STATIC / "ls_logo_transparent.png"  # background and ghost artefacts removed
# Served by Streamlit's static file serving (`enableStaticServing` in .streamlit/config.toml),
# relative to the app root so it resolves after a restart and behind a base URL path.
LOGO_URL = "app/static/ls_logo_transparent.png"
BACK_TO_TOP_JS = ASSETS / "back_to_top.js"


def logo_html() -> str:
    """The LS artwork (transparent derivative), sized by CSS only, aspect ratio preserved.

    The navy S has too little contrast on the dark header, so the artwork sits on a plain
    soft-white tile from the approved palette.
    """
    return (
        '<span class="ls-logo-tile">'
        f'<img class="ls-logo-img" src="{LOGO_URL}" alt="LaunchScout logo" /></span>'
    )


def inject_back_to_top() -> None:
    """Add the single floating Back to top button (client-side script, no rerun)."""
    script = BACK_TO_TOP_JS.read_text(encoding="utf-8")
    st.html(f"<script>{script}</script>", unsafe_allow_javascript=True)
