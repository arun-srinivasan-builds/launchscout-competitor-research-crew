"""LS logo and floating Back to top: presentation only, offline, no research or model calls."""

import hashlib
import importlib.util
import re
import struct
from pathlib import Path

import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest

from ui import chrome
from ui.theme import _CSS

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
LOGO_SHA256 = "bb95f5caaa07527f5efd5b0f41eaaba397d982a46a66fcadc649615fd0a6721e"
PNG_SIGNATURE = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def _markdown(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def _html(at: AppTest) -> list[str]:
    return [str(e.proto.body) for e in at.get("html")]


# ---------------------------------------------------------------- logo


def test_original_artwork_is_kept_unmodified_for_comparison():
    data = chrome.ORIGINAL_LOGO_FILE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == LOGO_SHA256
    assert data[:8] == PNG_SIGNATURE
    assert struct.unpack(">II", data[16:24]) == (1060, 803)


def _derived() -> np.ndarray:
    return np.asarray(Image.open(chrome.LOGO_FILE).convert("RGBA"))


def test_transparent_logo_has_no_background_ghosts_or_halo():
    a = _derived()
    alpha = a[..., 3]
    assert alpha[0, 0] == alpha[0, -1] == alpha[-1, 0] == alpha[-1, -1] == 0
    assert (alpha == 255).sum() > 50_000  # solid letters are intact
    # edge pixels carry the pure letter colour, so there is no white or grey fringe
    maroon, navy = np.array([108, 6, 34]), np.array([9, 38, 71])
    partial = a[(alpha > 0) & (alpha < 255)][:, :3].astype(int)
    assert len(partial) > 1000
    near = np.minimum(np.abs(partial - maroon).sum(axis=1), np.abs(partial - navy).sum(axis=1))
    # alpha 254 pixels are solid letter pixels kept as supplied (within a few levels)
    assert (near <= 16).all()
    edge = a[(alpha > 0) & (alpha < 254)][:, :3].astype(int)
    edge_near = np.minimum(np.abs(edge - maroon).sum(axis=1), np.abs(edge - navy).sum(axis=1))
    assert len(edge) > 1000 and (edge_near == 0).all()
    solid = a[alpha == 255][:, :3].astype(int)
    luma = 0.299 * solid[:, 0] + 0.587 * solid[:, 1] + 0.114 * solid[:, 2]
    assert luma.max() < 112  # nothing light is opaque


def test_transparent_logo_is_reproducible_from_the_supplied_artwork():
    script = ROOT / "scripts" / "make_ls_logo_transparent.py"
    spec = importlib.util.spec_from_file_location("make_ls_logo_transparent", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rendered, info = module.render()
    stored = Image.open(chrome.LOGO_FILE).convert("RGBA")
    assert rendered.size == stored.size == tuple(info["output_size"])
    assert np.array_equal(np.asarray(rendered), np.asarray(stored))
    x0, y0, x1, y1 = info["crop_box"]
    assert 0 <= x0 < x1 <= 1060 and 0 <= y0 < y1 <= 803  # a crop of the original canvas


def test_logo_is_served_from_a_relative_static_url_and_config_enables_it():
    assert chrome.LOGO_URL == "app/static/ls_logo_transparent.png"
    assert not chrome.LOGO_URL.startswith(("/", "http", "file:", "data:"))
    assert chrome.LOGO_FILE == ROOT / "static" / "ls_logo_transparent.png"
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert re.search(r"enableStaticServing\s*=\s*true", config)


def test_header_uses_the_logo_tile_and_keeps_title_and_tagline():
    md = _markdown(_app())
    assert 'class="ls-logo-tile"' in md and 'class="ls-logo-img"' in md
    assert chrome.LOGO_URL in md and 'alt="LaunchScout logo"' in md
    assert 'class="ls-logo"' not in md  # the single-letter mark is gone
    assert "LaunchScout" in md and "Competitor Research Crew" in md
    assert "From market intelligence to launch strategy." in md


def test_logo_tile_sizes_match_the_spec_without_distortion_or_effects():
    tile = re.search(r"\.ls-logo-tile\s*\{([^}]*)\}", _CSS).group(1)
    assert "height: 2.75rem" in tile  # 44 px
    assert "#F7F9FB" in tile  # soft-white from the approved palette
    img = re.search(r"\.ls-logo-img\s*\{([^}]*)\}", _CSS).group(1)
    assert "width: auto" in img  # aspect ratio preserved
    for block in (tile, img):
        assert "gradient" not in block and "animation" not in block
        assert "box-shadow" not in block
    mobile = _CSS[_CSS.index("max-width: 640px") :]
    assert ".ls-logo-tile { height: 2.5rem" in mobile  # 40 px on phones


def test_logo_asset_set_is_exactly_original_plus_derivative():
    pngs = [p for p in ROOT.rglob("*.png") if ".venv" not in p.parts and "shots" not in p.parts]
    rel = sorted(p.relative_to(ROOT).as_posix() for p in pngs)
    assert rel == ["static/ls_logo.png", "static/ls_logo_transparent.png"]


# ---------------------------------------------------------------- back to top


def test_back_to_top_is_injected_once_for_the_whole_app():
    at = _app()
    scripts = [h for h in _html(at) if "ls-back-to-top" in h]
    assert len(scripts) == 1  # app level, so Pitch Deck and Weekly Tracking get it too
    again = at.run()
    assert len([h for h in _html(again) if "ls-back-to-top" in h]) == 1  # none added on rerun


def test_back_to_top_script_contract():
    js = chrome.BACK_TO_TOP_JS.read_text(encoding="utf-8")
    assert 'setAttribute("aria-label", "Back to top")' in js
    assert "THRESHOLD = 400" in js
    assert "behavior" in js and "prefers-reduced-motion" in js
    assert "getElementById(ID)" in js  # reuses an existing button instead of adding another
    assert "__lsBackToTopCleanup" in js  # listeners are replaced on rerender
    # purely client side: no network, no navigation, no Streamlit messaging
    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "location.",
        "localStorage",
        "sessionStorage",
        "postMessage",
        "streamlit",
    ):
        assert forbidden not in js, forbidden


def test_back_to_top_script_survives_streamlit_html_sanitiser():
    """DOMPurify (used by st.html) drops a script containing markup-looking text; the live
    page showed an empty element until the icon was built with DOM calls."""
    js = chrome.BACK_TO_TOP_JS.read_text(encoding="utf-8")
    assert re.search(r"<[/\w!]", js) is None
    assert "createElementNS" in js


def test_back_to_top_styles_match_the_spec():
    css = re.search(r"\.ls-top\s*\{([^}]*)\}", _CSS).group(1)
    assert "position: fixed" in css and "right: 1rem" in css
    assert "width: 44px" in css and "height: 44px" in css
    assert "border-radius: 12px" in css and "var(--ls-teal)" in css and "var(--ls-base)" in css
    assert "visibility: hidden" in css  # not shown (and not focusable) until scrolled
    assert ".ls-top.ls-top-show { visibility: visible; opacity: 1; }" in _CSS
    assert ".ls-top:focus-visible" in _CSS  # visible keyboard focus state


def test_no_inline_style_attributes_or_extra_calls_in_chrome_module():
    source = (ROOT / "ui" / "chrome.py").read_text(encoding="utf-8")
    assert not re.search(r"style\s*=\s*[\"']", source)
    for name in ("crewai", "openai", "build_llm", "serper", "get_manager"):
        assert name not in source


def test_chrome_makes_no_llm_or_research_calls(monkeypatch):
    hits: list[str] = []

    def trap(name):
        def _fail(*a, **k):
            hits.append(name)
            raise AssertionError(name)

        return _fail

    monkeypatch.setattr("launchscout.llm.build_llm", trap("build_llm"))
    monkeypatch.setattr("crewai.LLM.call", trap("LLM.call"))
    monkeypatch.setattr("launchscout.tools._default_search", trap("serper"))
    monkeypatch.setattr("launchscout.runner.run_crew", trap("crew"))
    at = _app()
    for _ in range(3):
        at.run()
    assert hits == [] and not at.exception
