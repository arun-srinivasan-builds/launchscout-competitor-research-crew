"""Centralized visual theme: the only module that contains component CSS.

Palette (WCAG AA, normal text >= 4.5:1; ratios computed, not estimated):
  navy       #0B2545  on soft-white #F7F9FB  = 14.6:1   (body text, headings)
  navy-2     #13315C  with #FFFFFF text       = 13.0:1   (primary buttons, hero)
  steel-blue #3F6E99  on #FFFFFF              =  5.4:1   (rules, accents)
  teal       #0F766E  on #FFFFFF              =  5.5:1   (ready indicators)
  teal       #0F766E  on teal-soft #DDF3F0    =  4.7:1   (ready pills)
  amber      #8A5A00  on #FFFFFF              =  5.9:1   (warnings/unavailable)
  amber      #8A5A00  on amber-soft #FBF0D9   =  5.2:1   (warning pills)
  muted      #4A5D73  on #F7F9FB              =  6.4:1   (captions)
Streamlit-native tokens (background, text, primary) are set in `.streamlit/config.toml`.
"""

from __future__ import annotations

import streamlit as st

TAB_LABELS: tuple[str, str, str] = ("Research Workspace", "Pitch Deck", "Weekly Tracking")

PALETTE = {
    "navy": "#0B2545",
    "navy_2": "#13315C",
    "steel_blue": "#3F6E99",
    "teal": "#0F766E",
    "soft_white": "#F7F9FB",
}

_CSS = """
<style>
:root {
  --ls-navy: #0B2545;
  --ls-navy-2: #13315C;
  --ls-steel: #3F6E99;
  --ls-steel-soft: #E4ECF4;
  --ls-teal: #0F766E;
  --ls-teal-soft: #DDF3F0;
  --ls-amber: #8A5A00;
  --ls-amber-soft: #FBF0D9;
  --ls-bg: #F7F9FB;
  --ls-surface: #FFFFFF;
  --ls-border: #D3DEE9;
  --ls-muted: #4A5D73;
  --ls-radius: 12px;
  --ls-shadow: 0 1px 2px rgba(11, 37, 69, 0.06), 0 4px 14px rgba(11, 37, 69, 0.05);
}
html, body, .stApp {
  font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
.block-container { max-width: 1120px; padding-top: 2.25rem; padding-bottom: 3rem; }

/* Header */
.ls-hero {
  background: linear-gradient(135deg, var(--ls-navy) 0%, var(--ls-navy-2) 60%, var(--ls-steel) 130%);
  color: #FFFFFF; border-radius: var(--ls-radius); padding: 1.75rem 2rem; margin-bottom: 1.5rem;
  box-shadow: var(--ls-shadow);
}
.ls-hero h1 {
  font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 .35rem 0; color: #FFFFFF;
}
.ls-hero p { margin: 0; font-size: 1.02rem; line-height: 1.5; color: #E4ECF4; max-width: 46rem; }

/* Tabs */
button[role="tab"] { font-weight: 600; font-size: 1rem; padding: .65rem 1.1rem; }
button[role="tab"][aria-selected="true"] { color: var(--ls-navy-2); }

/* Section headings */
h2, h3 { letter-spacing: -0.01em; }
.ls-section { margin: 1.75rem 0 .35rem 0; font-size: 1.15rem; font-weight: 700; color: var(--ls-navy); }
.ls-caption { color: var(--ls-muted); font-size: .93rem; line-height: 1.45; margin-bottom: .75rem; }

/* Cards */
.ls-card {
  background: var(--ls-surface); border: 1px solid var(--ls-border); border-radius: var(--ls-radius);
  padding: 1.1rem 1.25rem; margin: .5rem 0 1rem 0; box-shadow: var(--ls-shadow);
}
.ls-card h4 { margin: 0 0 .5rem 0; font-size: 1rem; color: var(--ls-navy); }
.ls-row { margin: .15rem 0; line-height: 1.5; }
.ls-muted { color: var(--ls-muted); font-size: .92rem; }

/* Status pills */
.ls-pill {
  display: inline-block; padding: .12rem .6rem; border-radius: 999px; font-size: .78rem;
  font-weight: 600; border: 1px solid var(--ls-border); margin: .1rem .3rem .1rem 0;
  background: var(--ls-steel-soft); color: var(--ls-navy-2);
}
.ls-pill-ok { background: var(--ls-teal-soft); color: var(--ls-teal); border-color: var(--ls-teal); }
.ls-pill-warn {
  background: var(--ls-amber-soft); color: var(--ls-amber); border-color: var(--ls-amber);
}
.ls-pill-idle { background: #FFFFFF; color: var(--ls-muted); border-color: var(--ls-border); }

/* Agent workflow */
.ls-step {
  background: var(--ls-surface); border: 1px solid var(--ls-border); border-top: 3px solid var(--ls-steel);
  border-radius: var(--ls-radius); padding: .9rem 1rem; height: 100%; box-shadow: var(--ls-shadow);
}
.ls-step-num {
  display: inline-block; width: 1.55rem; height: 1.55rem; line-height: 1.55rem; text-align: center;
  border-radius: 50%; background: var(--ls-navy-2); color: #FFFFFF; font-weight: 700;
  font-size: .85rem; margin-bottom: .45rem;
}
.ls-step-title { font-weight: 700; color: var(--ls-navy); margin-bottom: .2rem; }
.ls-step-desc { color: var(--ls-muted); font-size: .88rem; line-height: 1.4; margin-bottom: .5rem; }
.ls-manager { border-top-color: var(--ls-teal); margin-bottom: .75rem; }

/* Inputs and buttons */
div[data-testid="stForm"] {
  background: var(--ls-surface); border: 1px solid var(--ls-border); border-radius: var(--ls-radius);
  padding: 1.25rem 1.4rem; box-shadow: var(--ls-shadow);
}
div[data-testid="stTextInput"] label p, div[data-testid="stTextArea"] label p { font-weight: 600; }
button[kind="primaryFormSubmit"], button[kind="primary"] {
  background: var(--ls-navy-2); color: #FFFFFF; border: 0; font-weight: 600; padding: .55rem 1.4rem;
  border-radius: 8px;
}
button[kind="primaryFormSubmit"]:hover, button[kind="primary"]:hover { background: var(--ls-navy); }
button:disabled { opacity: .6; }
button:focus-visible, input:focus-visible, textarea:focus-visible, [role="tab"]:focus-visible {
  outline: 3px solid var(--ls-teal); outline-offset: 2px;
}

/* Expander */
div[data-testid="stExpander"] {
  border: 1px solid var(--ls-border); border-radius: var(--ls-radius); background: var(--ls-surface);
}

/* Responsive */
@media (max-width: 760px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 1rem; }
  .ls-hero { padding: 1.25rem 1.1rem; }
  .ls-hero h1 { font-size: 1.55rem; }
}
</style>
"""


def inject_theme() -> None:
    """Inject the single CSS block. Call once per script run, before building tabs."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="ls-hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True
    )


def section(title: str, caption: str = "") -> None:
    """Section heading with optional caption."""
    html = f'<div class="ls-section">{title}</div>'
    if caption:
        html += f'<div class="ls-caption">{caption}</div>'
    st.markdown(html, unsafe_allow_html=True)


def pill(text: str, kind: str = "") -> str:
    """Return HTML for a status pill; kind is '', 'ok', 'warn' or 'idle'."""
    cls = {"ok": " ls-pill-ok", "warn": " ls-pill-warn", "idle": " ls-pill-idle"}.get(kind, "")
    return f'<span class="ls-pill{cls}">{text}</span>'
