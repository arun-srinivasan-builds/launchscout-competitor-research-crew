"""Centralized visual theme: the only module that contains component CSS.

Dark "mission control" theme matching the approved workflow reference. Palette keeps the
navy / steel-blue / teal identity on a deep-navy base; per-agent accents are green, amber,
sky-blue and orange. Contrast ratios (computed, WCAG relative luminance):
  text #E8EEF8 on base #050C1C = 16.7:1    text on surface #0C1830 = 15.2:1
  muted #9FB2CC on canvas #07112A = 8.7:1  muted on surface-2 #112244 = 7.3:1
  teal #2DD4BF on base = 10.5:1            warn #FBBF24 on surface = 10.6:1
  accents on card #0A1429: green 9.5, amber 12.0, blue 8.6, orange 8.1 (all :1)
  white on button teal #0F766E = 5.5:1
Streamlit-native tokens (background, text, primary) are set in `.streamlit/config.toml`.
"""

from __future__ import annotations

import streamlit as st

from ui.chrome import logo_html

TAB_LABELS: tuple[str, str, str] = ("Research Workspace", "Pitch Deck", "Weekly Tracking")

PALETTE = {
    "base": "#050C1C",
    "surface": "#0C1830",
    "surface_2": "#112244",
    "border": "#27406B",
    "text": "#E8EEF8",
    "muted": "#9FB2CC",
    "steel_blue": "#3F6E99",
    "teal": "#2DD4BF",
}

_CSS = """
<style>
:root {
  --ls-base: #050C1C;
  --ls-surface: #0C1830;
  --ls-surface-2: #112244;
  --ls-border: #27406B;
  --ls-text: #E8EEF8;
  --ls-muted: #9FB2CC;
  --ls-steel: #3F6E99;
  --ls-teal: #2DD4BF;
  --ls-green: #34D399;
  --ls-amber: #FACC15;
  --ls-blue: #38BDF8;
  --ls-orange: #FB923C;
  --ls-purple: #8B5CF6;
  --ls-warn: #FBBF24;
  --ls-radius: 14px;
}
html, body, .stApp {
  font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
.stApp {
  background:
    radial-gradient(900px 420px at 15% -5%, rgba(63, 110, 153, 0.28), transparent 70%),
    radial-gradient(800px 400px at 90% 10%, rgba(139, 92, 246, 0.14), transparent 70%),
    var(--ls-base);
}
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: min(1480px, 100%); padding: 1.75rem 2rem 3rem 2rem; }

/* Floating Back to top (created once by ui/assets/back_to_top.js) */
.ls-top {
  position: fixed; right: 1rem; bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
  z-index: 1000; width: 44px; height: 44px; padding: 0; display: grid; place-items: center;
  border-radius: 12px; border: 1.5px solid var(--ls-teal); background: var(--ls-base);
  color: var(--ls-teal); cursor: pointer; box-shadow: 0 2px 10px rgba(5, 12, 28, 0.6);
  visibility: hidden; opacity: 0; transition: opacity .18s ease, visibility .18s ease;
}
.ls-top.ls-top-show { visibility: visible; opacity: 1; }
.ls-top:hover { background: var(--ls-surface); }
.ls-top:focus-visible { outline: 3px solid var(--ls-teal); outline-offset: 3px; }
@media (prefers-reduced-motion: reduce) { .ls-top { transition: none; } }

/* Header band */
.ls-hero {
  display: flex; align-items: center; gap: 1.1rem; padding: 1.1rem 1.5rem; margin-bottom: 1.25rem;
  background: linear-gradient(135deg, rgba(17, 34, 68, 0.95), rgba(12, 24, 48, 0.95));
  border: 1px solid var(--ls-border); border-radius: var(--ls-radius);
  box-shadow: 0 0 24px rgba(56, 189, 248, 0.08);
}
/* LS artwork on a plain soft-white tile; the tile is the 44px (40px on phones) element */
.ls-logo-tile {
  flex: none; display: grid; place-items: center; height: 2.75rem; box-sizing: border-box;
  padding: .25rem .5rem; border-radius: 8px; background: #F7F9FB;
}
.ls-logo-img { height: 2.25rem; width: auto; display: block; }
.ls-hero-text { min-width: 0; }
.ls-hero h1 {
  font-size: 1.9rem; font-weight: 800; letter-spacing: .02em; margin: 0; padding: 0;
  color: var(--ls-text); line-height: 1.15;
}
.ls-hero-sub { font-size: 1.1rem; font-weight: 600; color: var(--ls-teal); margin-top: .1rem; }
.ls-hero-tag { font-size: 1rem; color: var(--ls-muted); margin-top: .15rem; }

/* Tabs */
div[data-baseweb="tab-list"] { gap: .35rem; }
button[role="tab"] { padding: .7rem 1.25rem; }
button[role="tab"] p { font-weight: 600; font-size: 1.1rem; color: var(--ls-muted); }
button[role="tab"][aria-selected="true"] p { color: var(--ls-text); }
div[data-baseweb="tab-highlight"] { background-color: var(--ls-teal); height: 3px; }

/* Body text and form labels */
div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] li {
  font-size: 1.05rem; line-height: 1.6;
}
div[data-testid="stWidgetLabel"] p, div[data-testid="stRadio"] label p,
div[data-testid="stTextInput"] label p, div[data-testid="stTextArea"] label p {
  font-size: 1.05rem; font-weight: 600; color: var(--ls-text);
}
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea { font-size: 1.05rem; }
div[data-testid="stCaptionContainer"], div[data-testid="stCaptionContainer"] p {
  font-size: .98rem; color: var(--ls-muted);
}

/* Section headings and captions */
.ls-section {
  margin: 1.6rem 0 .3rem 0; font-size: 1.3rem; font-weight: 700; color: var(--ls-text);
  letter-spacing: .01em;
}
.ls-caption { color: var(--ls-muted); font-size: 1.02rem; line-height: 1.55; margin-bottom: .75rem; }
/* Every section header reserves two caption lines so side-by-side panels start their
   content at the same level whatever the caption length. */
.ls-head .ls-caption { min-height: calc(2 * 1.55em); }

/* Cards */
.ls-card {
  background: var(--ls-surface); border: 1px solid var(--ls-border); border-radius: var(--ls-radius);
  padding: 1.1rem 1.25rem; margin: .5rem 0 1rem 0;
}
.ls-card h4 { margin: 0 0 .5rem 0; font-size: 1.12rem; color: var(--ls-text); }
.ls-row { margin: .15rem 0; line-height: 1.55; font-size: 1.04rem; }
.ls-muted { color: var(--ls-muted); font-size: 1rem; }

/* Status pills */
.ls-pill {
  display: inline-block; padding: .14rem .65rem; border-radius: 999px; font-size: .86rem;
  font-weight: 600; border: 1px solid var(--ls-border); margin: .1rem .3rem .1rem 0;
  background: var(--ls-surface-2); color: var(--ls-text);
}
.ls-pill-ok { background: rgba(45, 212, 191, 0.14); color: var(--ls-teal); border-color: var(--ls-teal); }
.ls-pill-warn {
  background: rgba(251, 191, 36, 0.14); color: var(--ls-warn); border-color: var(--ls-warn);
}
.ls-pill-idle { background: transparent; color: var(--ls-muted); border-color: var(--ls-border); }

/* Live Agent Workflow canvas */
.ls-canvas {
  position: relative; padding: 1.5rem 1.5rem .75rem 1.5rem; margin: 0 0 1.25rem 0;
  border: 1px solid var(--ls-border); border-radius: 18px; overflow: hidden;
  background:
    linear-gradient(rgba(63, 110, 153, 0.10) 1px, transparent 1px) 0 0 / 32px 32px,
    linear-gradient(90deg, rgba(63, 110, 153, 0.10) 1px, transparent 1px) 0 0 / 32px 32px,
    radial-gradient(700px 300px at 50% 0%, rgba(56, 189, 248, 0.10), transparent 70%),
    #07112A;
}
.ls-flow {
  --ls-gap: 1.1rem;
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: var(--ls-gap);
  align-items: stretch;
}
.ls-manager-node {
  grid-row: 1; grid-column: 1 / -1; justify-self: center; width: min(560px, 100%);
  box-sizing: border-box; margin-bottom: .2rem; padding: .9rem 1rem; border-radius: var(--ls-radius);
  border: 1.5px solid var(--ls-purple); background: rgba(139, 92, 246, 0.10);
  box-shadow: 0 0 18px rgba(139, 92, 246, 0.35);
}
.ls-manager-node .ls-glyph { color: var(--ls-purple); border-color: var(--ls-purple); }
.ls-manager-node .ls-node-status { color: var(--ls-muted); }
.ls-manager-node.ls-st-active .ls-node-status,
.ls-manager-node.ls-st-complete .ls-node-status { color: #C4B5FD; }
.ls-manager-node .ls-chip { margin-top: .5rem; }
.ls-manager-node .ls-task { margin: .55rem 0; }
.ls-mgr-cols { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .6rem; margin-top: .55rem; }
/* delegation lines: Manager bus to each specialist (dashed, distinct from the flow arcs) */
.ls-mgr-links {
  grid-row: 2; grid-column: 1 / -1; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
  column-gap: var(--ls-gap, 1.1rem); position: relative; height: 34px; margin-top: 14px;
}
.ls-mgr-links::before {
  content: ""; position: absolute; left: 50%; top: -14px; height: 14px; width: 0;
  border-left: 2px dashed var(--ls-purple); margin-left: -1px;
}
.ls-drop { position: relative; }
.ls-drop::before {
  content: ""; position: absolute; top: 0; left: 0; right: calc(-1 * var(--ls-gap, 1.1rem));
  border-top: 2px dashed var(--ls-purple);
}
.ls-drop:nth-child(1)::before { left: 22%; }
.ls-drop:nth-child(4)::before { right: 78%; }
.ls-drop::after {
  content: ""; position: absolute; left: 22%; top: 0; bottom: 6px; width: 0; margin-left: -1px;
  border-left: 2px dashed var(--ls-purple);
}
.ls-drop i {
  position: absolute; left: 22%; bottom: 0; margin-left: -6px; width: 0; height: 0;
  border-left: 6px solid transparent; border-right: 6px solid transparent;
  border-top: 8px solid var(--ls-purple);
}
.ls-vlink-mgr { display: none; }
.ls-arc { height: 46px; box-sizing: border-box; position: relative; }
.ls-arc-top {
  grid-row: 3; align-self: end; margin: 0 25%; border: 3px solid; border-bottom: 0;
  border-radius: 28px 28px 0 0;
  border-color: var(--ls-purple) var(--ls-purple) transparent var(--ls-blue);
  box-shadow: 0 -4px 14px rgba(139, 92, 246, 0.35);
}
.ls-arc-bottom {
  grid-row: 5; align-self: start; margin: 0 25%; border: 3px solid; border-top: 0;
  border-radius: 0 0 28px 28px;
  border-color: transparent var(--ls-purple) var(--ls-blue) var(--ls-blue);
  box-shadow: 0 4px 14px rgba(56, 189, 248, 0.35);
}
.ls-arc-12 { grid-column: 1 / 3; }
.ls-arc-23 { grid-column: 2 / 4; }
.ls-arc-34 { grid-column: 3 / 5; }
.ls-arc-top::after, .ls-arc-bottom::after {
  content: ""; position: absolute; width: 0; height: 0;
  border-left: 8px solid transparent; border-right: 8px solid transparent;
}
.ls-arc-top::after { right: -11px; bottom: -6px; border-top: 11px solid var(--ls-purple); }
.ls-arc-bottom::after { right: -11px; top: -6px; border-bottom: 11px solid var(--ls-purple); }
.ls-arc-top::before, .ls-arc-bottom::before {
  content: ""; position: absolute; width: 9px; height: 9px; border-radius: 50%;
  background: var(--ls-blue); box-shadow: 0 0 8px var(--ls-blue); left: -6px;
}
.ls-arc-top::before { bottom: -3px; }
.ls-arc-bottom::before { top: -3px; }
.ls-vlink { display: none; }

/* Agent nodes */
.ls-node {
  grid-row: 4; display: flex; flex-direction: column; gap: .7rem; box-sizing: border-box;
  padding: .9rem; border-radius: var(--ls-radius); min-height: 24rem;
  border: 1.5px solid var(--ls-accent);
  background: linear-gradient(180deg, var(--ls-tint), #0A1429 55%);
  box-shadow: 0 0 20px var(--ls-glow), inset 0 0 18px rgba(255, 255, 255, 0.02);
}
.ls-a1 {
  grid-column: 1; --ls-accent: var(--ls-green); --ls-tint: rgba(52, 211, 153, 0.14);
  --ls-glow: rgba(52, 211, 153, 0.30);
}
.ls-a2 {
  grid-column: 2; --ls-accent: var(--ls-amber); --ls-tint: rgba(250, 204, 21, 0.12);
  --ls-glow: rgba(250, 204, 21, 0.26);
}
.ls-a3 {
  grid-column: 3; --ls-accent: var(--ls-blue); --ls-tint: rgba(56, 189, 248, 0.14);
  --ls-glow: rgba(56, 189, 248, 0.30);
}
.ls-a4 {
  grid-column: 4; --ls-accent: var(--ls-orange); --ls-tint: rgba(251, 146, 60, 0.14);
  --ls-glow: rgba(251, 146, 60, 0.30);
}
.ls-node-head { display: flex; align-items: flex-start; gap: .85rem; }
.ls-glyph {
  position: relative; flex: none; width: 2.4rem; height: 2.4rem; border-radius: 10px;
  display: grid; place-items: center; font-size: 1.2rem; color: var(--ls-accent); border: 1.5px solid var(--ls-accent);
  background: rgba(255, 255, 255, 0.04);
}
.ls-node-id { display: flex; flex-direction: column; min-width: 0; flex: 1; justify-content: flex-start; }
.ls-node-name {
  font-weight: 800; font-size: .9rem; letter-spacing: .03em; text-transform: uppercase;
  color: var(--ls-text); line-height: 1.2; min-height: 2.4em;
}
.ls-manager-node .ls-node-name { min-height: 0; }
.ls-node-status { font-size: .95rem; font-weight: 600; color: var(--ls-accent); }
.ls-st-idle .ls-node-status { color: var(--ls-muted); }
.ls-st-failed .ls-node-status { color: #F87171; }
.ls-st-cancelled .ls-node-status { color: var(--ls-warn); }
.ls-st-active .ls-node { box-shadow: 0 0 26px var(--ls-glow); }
.ls-node-num {
  position: absolute; top: -.5rem; right: -.5rem; width: 1.3rem; height: 1.3rem; border-radius: 50%;
  display: grid; place-items: center; font-size: .75rem; font-weight: 700; color: var(--ls-base);
  background: var(--ls-accent);
}
.ls-task {
  padding: .5rem .65rem; border-radius: 10px; border: 1px solid var(--ls-border);
  background: rgba(5, 12, 28, 0.6);
}
.ls-task-row {
  display: flex; justify-content: space-between; gap: .5rem; font-size: .88rem; font-weight: 700;
  letter-spacing: .05em; text-transform: uppercase; color: var(--ls-text);
}
.ls-track { height: 6px; margin-top: .4rem; border-radius: 99px; background: #1B2D4F; overflow: hidden; }
.ls-fill { height: 100%; background: var(--ls-accent); border-radius: 99px; width: 0; }
.ls-p-10 { width: 10%; } .ls-p-20 { width: 20%; } .ls-p-30 { width: 30%; } .ls-p-40 { width: 40%; }
.ls-p-50 { width: 50%; } .ls-p-60 { width: 60%; } .ls-p-70 { width: 70%; } .ls-p-80 { width: 80%; }
.ls-p-90 { width: 90%; } .ls-p-100 { width: 100%; }
.ls-panel {
  padding: .6rem .7rem; border-radius: 10px; border: 1px solid var(--ls-border);
  background: rgba(5, 12, 28, 0.55);
}
.ls-panel-title {
  font-size: .8rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
  color: var(--ls-muted); margin-bottom: .35rem;
}
.ls-gap { margin-top: .6rem; }
.ls-chips { display: flex; flex-wrap: wrap; gap: .35rem; margin-bottom: .5rem; }
.ls-chip {
  display: inline-block; padding: .2rem .55rem; border-radius: 8px; font-size: .85rem; font-weight: 600;
  color: var(--ls-text); border: 1px solid var(--ls-border); background: var(--ls-surface-2);
}
.ls-chip-warn { color: var(--ls-warn); border-color: var(--ls-warn); background: rgba(251, 191, 36, 0.12); }
.ls-panel-text { font-size: .95rem; line-height: 1.45; color: var(--ls-text); }
.ls-events { list-style: none; margin: 0; padding: 0; font-size: .92rem; color: var(--ls-text); }
div[data-testid="stMarkdownContainer"] .ls-events li { margin: .15rem 0; font-size: .84rem; line-height: 1.35; }
.ls-none { color: var(--ls-muted); }
.ls-handoff {
  margin-top: auto; display: flex; align-items: center; gap: .55rem; padding: .55rem .7rem;
  border-radius: 10px; border: 1px dashed var(--ls-accent); background: rgba(255, 255, 255, 0.03);
}
.ls-doc {
  flex: none; width: .95rem; height: 1.2rem; border-radius: 3px; border: 1.5px solid var(--ls-accent);
  opacity: .8;
}
.ls-handoff-text { font-size: .92rem; font-weight: 600; color: var(--ls-text); }
.ls-statusbar {
  display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-top: 1.2rem;
  padding-top: .6rem; border-top: 1px solid var(--ls-border); font-size: .92rem; color: var(--ls-muted);
}
.ls-dot {
  display: inline-block; width: .6rem; height: .6rem; border-radius: 50%; margin-right: .5rem;
  background: var(--ls-muted);
}

/* Connector motion: only connectors whose recorded state transition is happening carry
   .ls-live (see launchscout/progress.active_links); idle and finished flows stay still. */
.ls-arc-top::before, .ls-arc-bottom::before { opacity: .35; }
.ls-arc.ls-live { box-shadow: 0 0 16px rgba(45, 212, 191, 0.55); }
.ls-arc-top.ls-live { border-color: var(--ls-teal) var(--ls-teal) transparent var(--ls-teal); }
.ls-arc-bottom.ls-live { border-color: transparent var(--ls-teal) var(--ls-teal) var(--ls-teal); }
.ls-arc.ls-live::before {
  opacity: 1; background: var(--ls-teal); box-shadow: 0 0 10px var(--ls-teal); bottom: auto;
}
.ls-arc-top.ls-live::before { animation: ls-run-top 1.9s linear infinite; }
.ls-arc-bottom.ls-live::before { animation: ls-run-bottom 1.9s linear infinite; }
@keyframes ls-run-top {
  0% { left: -6px; top: calc(100% - 6px); }
  14% { left: -6px; top: -6px; }
  86% { left: calc(100% - 3px); top: -6px; }
  100% { left: calc(100% - 3px); top: calc(100% - 6px); }
}
@keyframes ls-run-bottom {
  0% { left: -6px; top: -3px; }
  14% { left: -6px; top: calc(100% - 6px); }
  86% { left: calc(100% - 3px); top: calc(100% - 6px); }
  100% { left: calc(100% - 3px); top: -3px; }
}
.ls-drop.ls-live::before { border-top-color: var(--ls-teal); }
.ls-drop.ls-live::after { border-left-color: var(--ls-teal); }
.ls-drop.ls-live i { border-top-color: var(--ls-teal); animation: ls-drop-pulse 1.1s ease-in-out infinite; }
@keyframes ls-drop-pulse {
  0%, 100% { transform: translateY(0); opacity: .6; }
  50% { transform: translateY(5px); opacity: 1; }
}
.ls-vlink.ls-live { background: linear-gradient(var(--ls-teal), var(--ls-blue), var(--ls-teal)); background-size: 100% 200%; animation: ls-vlink-run 1.2s linear infinite; }
@keyframes ls-vlink-run { from { background-position: 0 0; } to { background-position: 0 200%; } }
@media (prefers-reduced-motion: reduce) {
  .ls-arc.ls-live::before, .ls-drop.ls-live i, .ls-vlink.ls-live { animation: none; }
}
.ls-deleg { margin: 0; padding-left: 1.2rem; }
.ls-note { margin-top: .5rem; font-size: .85rem; color: var(--ls-muted); }
.ls-note summary { cursor: pointer; width: fit-content; }
.ls-note summary:focus-visible { outline: 3px solid var(--ls-teal); outline-offset: 2px; }
.ls-note p { margin: .35rem 0 0 0; }
.ls-replay-caption { font-size: .9rem; color: var(--ls-muted); }

/* Two-panel layout: sticky control panel on wide desktops, stacked at 1200px and below */
@media (min-width: 1201px) {
  .st-key-ls_left_panel { position: sticky; top: 1rem; }
}


/* Left control card */
.st-key-ls_left_card {
  background: var(--ls-surface); border: 1px solid var(--ls-border); border-radius: var(--ls-radius);
  padding: 1.1rem 1.1rem 1.25rem 1.1rem;
}

/* Inputs and buttons */
div[data-testid="stForm"] {
  background: var(--ls-surface); border: 1px solid var(--ls-border); border-radius: var(--ls-radius);
  padding: 1.25rem 1.4rem;
}
button[kind="primaryFormSubmit"], button[kind="primary"] {
  background: linear-gradient(135deg, #0F766E, #2563EB); color: #FFFFFF; border: 0;
  font-weight: 700; padding: .55rem 1.5rem; border-radius: 10px;
}
button[kind="primaryFormSubmit"] p, button[kind="primary"] p { color: #FFFFFF; font-size: 1.05rem; }
button[kind="primaryFormSubmit"]:hover, button[kind="primary"]:hover { filter: brightness(1.12); }
button:disabled { opacity: .6; }
button:focus-visible, input:focus-visible, textarea:focus-visible, [role="tab"]:focus-visible {
  outline: 3px solid var(--ls-teal); outline-offset: 2px;
}

/* Expander */
div[data-testid="stExpander"] {
  border: 1px solid var(--ls-border); border-radius: var(--ls-radius); background: var(--ls-surface);
}

/* Responsive: panels stack at 1200px; the four agent cards stay in one row down to 820px and
   stack with vertical connectors below that */
@media (max-width: 1100px) {
  .block-container { padding-left: 1.25rem; padding-right: 1.25rem; }
  .ls-canvas { padding: 1.1rem 1rem .6rem 1rem; }
  .ls-flow { --ls-gap: .75rem; }
  .ls-node { padding: .7rem; }
}
@media (max-width: 820px) {
  .ls-flow { grid-template-columns: minmax(0, 1fr); width: min(560px, 100%); margin: 0 auto; }
  .ls-arc, .ls-mgr-links { display: none; }
  .ls-mgr-cols { grid-template-columns: minmax(0, 1fr); }
  .ls-node, .ls-a1, .ls-a2, .ls-a3, .ls-a4, .ls-manager-node { grid-row: auto; grid-column: 1; }
  .ls-node { min-height: 0; }
  .ls-node-name { min-height: 0; }
  .ls-vlink {
    display: block; position: relative; height: 38px; width: 3px; margin: 0 auto;
    background: linear-gradient(var(--ls-blue), var(--ls-purple));
    box-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
  }
  .ls-vlink::after {
    content: ""; position: absolute; left: -6px; bottom: -4px; width: 0; height: 0;
    border-left: 7.5px solid transparent; border-right: 7.5px solid transparent;
    border-top: 10px solid var(--ls-purple);
  }
}
@media (max-width: 1200px) {
  div[data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  div[data-testid="stColumn"] { min-width: 100% !important; flex: 1 1 100% !important; }
}
@media (max-width: 640px) {
  .block-container { padding-left: .75rem; padding-right: .75rem; padding-top: .75rem; }
  .ls-hero { padding: .9rem 1rem; gap: .8rem; }
  .ls-hero h1 { font-size: 1.5rem; }
  .ls-logo-tile { height: 2.5rem; padding: .25rem .45rem; }
  .ls-logo-img { height: 2rem; }
  button[role="tab"] { padding: .6rem .7rem; }
  button[role="tab"] p { font-size: 1rem; }
  .ls-canvas { padding: .8rem .6rem .5rem .6rem; }
}
/* Demo-mode notices (rendered only in demo mode) */
:root { --ls-rose: #FB7185; --ls-rose-bg: rgba(127, 29, 29, 0.38); --ls-rose-line: #BE3455; }
.ls-demo-badge {
  flex: none; margin-left: auto; display: flex; align-items: center; gap: .65rem;
  padding: .55rem .9rem; border: 1px solid var(--ls-steel); border-radius: 12px;
  background: rgba(12, 24, 48, 0.85); box-shadow: 0 0 14px rgba(56, 189, 248, 0.12);
}
.ls-demo-badge svg { flex: none; width: 1.7rem; height: 1.7rem; color: var(--ls-amber); }
.ls-demo-badge-title { font-weight: 800; letter-spacing: .06em; color: var(--ls-amber); font-size: 1rem; }
.ls-demo-badge-line { font-size: .85rem; color: var(--ls-text); line-height: 1.35; }
.ls-demo-banner {
  display: flex; flex-wrap: wrap; align-items: center; gap: .9rem 1.4rem; box-sizing: border-box;
  padding: .85rem 1.1rem; margin: 0 0 1rem 0; border-radius: var(--ls-radius);
  border: 1px solid var(--ls-rose-line); background: var(--ls-rose-bg);
}
.ls-demo-banner-main { display: flex; align-items: center; gap: .9rem; flex: 1 1 22rem; min-width: 0; }
.ls-demo-banner-main svg { flex: none; width: 2.4rem; height: 2.4rem; color: var(--ls-rose); }
.ls-demo-banner-title { font-size: 1.15rem; font-weight: 800; color: #FFB4BF; line-height: 1.3; }
.ls-demo-banner-text { font-size: .98rem; color: var(--ls-text); margin-top: .15rem; line-height: 1.4; }
.ls-demo-chips { display: flex; flex-wrap: wrap; gap: .6rem 1.1rem; flex: 0 1 auto; }
.ls-demo-chip { display: flex; align-items: center; gap: .5rem; font-size: .9rem; color: var(--ls-text); }
.ls-demo-chip svg { flex: none; width: 1.4rem; height: 1.4rem; color: var(--ls-rose); }
.ls-demo-chip.ok svg { color: var(--ls-teal); }
.ls-demo-guide {
  display: flex; align-items: center; gap: .9rem; box-sizing: border-box;
  padding: .8rem 1.1rem; margin: .25rem 0 1rem 0; border-radius: var(--ls-radius);
  border: 1px solid var(--ls-steel);
  background: linear-gradient(90deg, rgba(14, 58, 112, 0.75), rgba(12, 24, 48, 0.9));
}
.ls-demo-guide svg { flex: none; width: 2rem; height: 2rem; color: var(--ls-blue); }
.ls-demo-guide-title { font-size: 1.2rem; font-weight: 800; color: var(--ls-text); line-height: 1.3; }
.ls-demo-guide-text { font-size: .98rem; color: #CFE0F5; margin-top: .1rem; line-height: 1.4; }
.ls-demo-note {
  display: flex; align-items: center; gap: .65rem; box-sizing: border-box;
  padding: .6rem .8rem; margin: .5rem 0 .75rem 0; border-radius: 10px;
  border: 1px solid var(--ls-rose-line); background: var(--ls-rose-bg);
  font-size: .95rem; font-weight: 600; color: #FFD5DB; line-height: 1.4;
}
.ls-demo-note svg { flex: none; width: 1.5rem; height: 1.5rem; color: var(--ls-rose); }
@media (max-width: 820px) {
  .ls-hero { flex-wrap: wrap; }
  .ls-demo-badge { margin-left: 0; width: 100%; box-sizing: border-box; }
}
@media (max-width: 640px) {
  .ls-demo-banner { padding: .75rem .85rem; }
  .ls-demo-banner-title { font-size: 1.05rem; }
  .ls-demo-guide-title { font-size: 1.08rem; }
  .ls-demo-banner-main svg { width: 1.9rem; height: 1.9rem; }
}
</style>
"""


COCKPIT_CSS = """
<style>
.ck-wrap { margin: .25rem 0 1rem 0; }
div[data-testid="stButtonGroup"] > div { flex-wrap: wrap; overflow: visible; row-gap: .4rem; }
div[data-testid="stButtonGroup"] button p { font-size: .98rem; font-weight: 600; }
.ck-eyebrow {
  font-size: .8rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  color: var(--ls-muted); margin-bottom: .35rem;
}
.ck-hero {
  border: 1px solid var(--ls-border); border-radius: 18px; padding: 1.1rem 1.25rem;
  background:
    radial-gradient(600px 220px at 0% 0%, rgba(45, 212, 191, 0.10), transparent 70%),
    radial-gradient(500px 200px at 100% 0%, rgba(139, 92, 246, 0.10), transparent 70%),
    var(--ls-surface);
}
.ck-chips { display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: .75rem; }
.ck-chip {
  display: inline-flex; align-items: center; gap: .45rem; padding: .35rem .8rem;
  border-radius: 999px; font-size: .92rem; font-weight: 700; border: 1px solid var(--ls-border);
  background: var(--ls-surface-2); color: var(--ls-text);
}
.ck-chip small { font-weight: 500; color: var(--ls-muted); }
.ck-dot { width: .6rem; height: .6rem; border-radius: 50%; background: var(--ls-muted); }
.ck-ok { border-color: var(--ls-teal); }
.ck-ok .ck-dot { background: var(--ls-teal); }
.ck-bad { border-color: #F87171; }
.ck-bad .ck-dot { background: #F87171; }
.ck-warn { border-color: var(--ls-warn); }
.ck-warn .ck-dot { background: var(--ls-warn); }
.ck-take { font-size: 1.12rem; line-height: 1.6; color: var(--ls-text); margin: .1rem 0 .9rem 0; }
.ck-take b { color: var(--ls-teal); }
.ck-kpis {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(124px, 1fr)); gap: .7rem;
}
@media (max-width: 900px) { .ck-kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 520px) { .ck-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.ck-kpi {
  border: 1px solid var(--ls-border); border-radius: 14px; padding: .7rem .85rem;
  background: rgba(5, 12, 28, 0.55);
}
.ck-kpi-top { display: flex; align-items: baseline; gap: .35rem; }
.ck-kpi-val { font-size: 1.7rem; font-weight: 800; color: var(--ls-text); line-height: 1.1; }
.ck-kpi-of { font-size: .95rem; color: var(--ls-muted); }
.ck-kpi-label { font-size: .86rem; color: var(--ls-muted); margin-top: .15rem; }
.ck-bar { height: 6px; border-radius: 99px; background: #1B2D4F; margin-top: .55rem; }
.ck-fill { height: 100%; border-radius: 99px; width: 0; background: var(--ls-teal); }
.ck-fill.ck-low { background: #F87171; }
.ck-fill.ck-mid { background: var(--ls-warn); }
.ck-w-0 { width: 0; } .ck-w-5 { width: 5%; } .ck-w-10 { width: 10%; } .ck-w-15 { width: 15%; }
.ck-w-20 { width: 20%; } .ck-w-25 { width: 25%; } .ck-w-30 { width: 30%; } .ck-w-35 { width: 35%; }
.ck-w-40 { width: 40%; } .ck-w-45 { width: 45%; } .ck-w-50 { width: 50%; } .ck-w-55 { width: 55%; }
.ck-w-60 { width: 60%; } .ck-w-65 { width: 65%; } .ck-w-70 { width: 70%; } .ck-w-75 { width: 75%; }
.ck-w-80 { width: 80%; } .ck-w-85 { width: 85%; } .ck-w-90 { width: 90%; } .ck-w-95 { width: 95%; }
.ck-w-100 { width: 100%; }
.ck-block {
  margin-top: .85rem; padding: .7rem .9rem; border-radius: 12px; font-size: .98rem;
  border: 1px solid var(--ls-warn); background: rgba(251, 191, 36, 0.08); color: var(--ls-text);
}
.ck-block.ck-pass { border-color: var(--ls-teal); background: rgba(45, 212, 191, 0.08); }
.ck-block ul { margin: .35rem 0 0 1.1rem; padding: 0; }
.ck-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: .9rem; }
.ck-card {
  border: 1px solid var(--ls-border); border-radius: 16px; padding: 1rem 1.05rem;
  background: var(--ls-surface); display: flex; flex-direction: column; gap: .6rem;
}
.ck-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: .6rem; }
.ck-card h4 { margin: 0; font-size: 1.12rem; color: var(--ls-text); line-height: 1.25; }
.ck-site { font-size: .88rem; color: var(--ls-muted); overflow-wrap: anywhere; }
.ck-badge {
  display: inline-block; padding: .15rem .6rem; border-radius: 999px; font-size: .78rem;
  font-weight: 700; border: 1px solid var(--ls-border); background: var(--ls-surface-2);
  color: var(--ls-text); white-space: nowrap;
}
.ck-badge.ck-ok { border-color: var(--ls-teal); color: var(--ls-teal); background: rgba(45,212,191,.1); }
.ck-badge.ck-bad { border-color: #F87171; color: #F87171; background: rgba(248,113,113,.1); }
.ck-badge.ck-warn { border-color: var(--ls-warn); color: var(--ls-warn); background: rgba(251,191,36,.1); }
.ck-badge.ck-rec { border-color: var(--ls-purple); color: #C4B5FD; background: rgba(139,92,246,.12); }
.ck-field { font-size: .96rem; line-height: 1.5; color: var(--ls-text); }
.ck-field span.ck-k {
  display: block; font-size: .76rem; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; color: var(--ls-muted); margin-bottom: .1rem;
}
.ck-tags { display: flex; flex-wrap: wrap; gap: .35rem; }
.ck-tag {
  padding: .12rem .55rem; border-radius: 8px; font-size: .82rem; font-weight: 600;
  background: var(--ls-surface-2); border: 1px solid var(--ls-border); color: var(--ls-text);
}
.ck-srcs { display: flex; flex-direction: column; gap: .3rem; }
.ck-src a {
  color: #7DD3FC; text-decoration: none; font-size: .93rem; overflow-wrap: anywhere;
  border-bottom: 1px dotted rgba(125, 211, 252, 0.5);
}
.ck-src a:hover { color: #BAE6FD; }
.ck-src small { color: var(--ls-muted); margin-left: .35rem; }
.ck-quote {
  border-left: 3px solid var(--ls-teal); padding: .45rem .8rem; margin: .35rem 0;
  background: rgba(5, 12, 28, 0.45); border-radius: 0 10px 10px 0; font-size: .97rem;
  line-height: 1.5;
}
.ck-quote.ck-complaint { border-left-color: #F87171; }
.ck-road { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: .9rem; }
.ck-week {
  position: relative; border: 1px solid var(--ls-border); border-top: 3px solid var(--ls-blue);
  border-radius: 14px; padding: .85rem .9rem; background: var(--ls-surface);
}
.ck-week:nth-child(2) { border-top-color: var(--ls-teal); }
.ck-week:nth-child(3) { border-top-color: var(--ls-amber); }
.ck-week:nth-child(4) { border-top-color: var(--ls-orange); }
.ck-week-num { font-size: .78rem; font-weight: 800; letter-spacing: .08em; color: var(--ls-muted); }
.ck-week h5 { margin: .15rem 0 .5rem 0; font-size: 1.02rem; color: var(--ls-text); }
.ck-week ul { margin: .4rem 0 0 0; padding-left: 1.05rem; font-size: .9rem; line-height: 1.45; }
.ck-week li { margin: .25rem 0; }
.ck-rules { display: flex; flex-direction: column; gap: .45rem; }
.ck-rule {
  display: grid; grid-template-columns: 3.2rem 1fr auto; gap: .7rem; align-items: start;
  border: 1px solid var(--ls-border); border-radius: 12px; padding: .6rem .8rem;
  background: var(--ls-surface);
}
.ck-rule-id { font-weight: 800; color: var(--ls-muted); }
.ck-rule-title { font-weight: 700; color: var(--ls-text); }
.ck-rule-detail { font-size: .92rem; color: var(--ls-muted); margin-top: .1rem; }
.ck-note { font-size: .9rem; color: var(--ls-muted); margin: .4rem 0 .6rem 0; }
.ck-h { font-size: 1.12rem; font-weight: 700; margin: 1rem 0 .5rem 0; color: var(--ls-text); }
.st-key-ck_actions {
  border: 1px solid var(--ls-border); border-radius: 14px; background: var(--ls-surface);
  padding: .65rem .85rem .75rem .85rem; margin: .8rem 0 .9rem 0;
}
.ck-actions-title {
  font-size: .8rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase;
  color: var(--ls-muted); margin-bottom: .45rem;
}
.st-key-ck_actions div[data-testid="stDownloadButton"] button {
  width: 100%; min-height: 2.7rem; font-weight: 700;
}
@media (min-width: 521px) {
  /* keep the two downloads side by side even where the main panels have stacked */
  .st-key-ck_actions div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
  .st-key-ck_actions div[data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 0 !important; }
}
.st-key-ck_nav div[data-testid="stButtonGroup"] > div {
  flex-wrap: wrap; overflow: visible; row-gap: .45rem; column-gap: .4rem;
}
/* Business intelligence (first four) vs trust and engineering (last two) */
.st-key-ck_nav div[data-testid="stButtonGroup"] > div > button:nth-child(-n+4) {
  border-color: rgba(45, 212, 191, 0.55);
}
.st-key-ck_nav div[data-testid="stButtonGroup"] > div > button:nth-child(n+5) {
  border-color: rgba(167, 139, 250, 0.7); background: rgba(139, 92, 246, 0.10);
}
.st-key-ck_nav div[data-testid="stButtonGroup"] > div > button:nth-child(5) { margin-left: .9rem; }
.st-key-ck_nav div[data-testid="stButtonGroup"] button p { font-size: .9rem; }
/* long URLs and tables never widen the page when the full report is opened */
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] {
  overflow-wrap: anywhere; word-break: break-word; max-width: 100%;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] table {
  display: block; max-width: 100%; overflow-x: auto;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] th,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] td {
  overflow-wrap: normal; word-break: normal; min-width: 7rem; vertical-align: top;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] td a {
  overflow-wrap: anywhere; word-break: break-all;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] pre,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] code {
  white-space: pre-wrap; overflow-wrap: anywhere;
}
@media (max-width: 640px) {
  .ck-hero { padding: .9rem .9rem; }
  .ck-take { font-size: 1.02rem; }
  .ck-kpi-val { font-size: 1.45rem; }
  .ck-rule { grid-template-columns: 2.6rem 1fr; }
  .ck-rule .ck-badge { grid-column: 2; justify-self: start; }
  .ck-grid { grid-template-columns: minmax(0, 1fr); }
  /* report tables on phones: fixed layout, every cell wraps; nothing is hidden or scrolls */
  div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] table {
    display: table; width: 100%; table-layout: fixed;
  }
  div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] th,
  div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] td {
    min-width: 0; overflow-wrap: anywhere; word-break: break-word; font-size: .85rem;
    padding: .35rem .4rem;
  }
}
</style>
"""


TRACKING_CSS = """
<style>
:root {
  --tk-burgundy: #C0566B; --tk-burgundy-bg: rgba(127, 29, 29, 0.30);
  --tk-gold: #D9B45B; --tk-gold-bg: rgba(217, 180, 91, 0.10);
}
.tk-hero {
  display: flex; flex-wrap: wrap; align-items: center; gap: 1rem 1.2rem; box-sizing: border-box;
  padding: 1.1rem 1.4rem; margin: .25rem 0 1rem 0; border-radius: var(--ls-radius);
  border: 1px solid var(--ls-border);
  background: linear-gradient(135deg, rgba(17, 34, 68, 0.95), rgba(12, 24, 48, 0.95));
  box-shadow: 0 0 24px rgba(56, 189, 248, 0.08);
}
.tk-hero-text { flex: 1 1 18rem; min-width: 0; }
.tk-eyebrow { font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
  color: var(--ls-teal); }
.tk-hero h2 { margin: .1rem 0 0 0; padding: 0; font-size: 1.7rem; font-weight: 800;
  color: var(--ls-text); line-height: 1.2; }
.tk-sub { margin-top: .25rem; font-size: 1rem; color: var(--ls-muted); line-height: 1.45; }
.tk-hero-chips { display: flex; flex-wrap: wrap; gap: .5rem; flex: 0 1 auto; }
.tk-chip { font-size: .8rem; font-weight: 700; padding: .3rem .65rem; border-radius: 999px;
  border: 1px solid var(--ls-steel); color: var(--ls-text); background: rgba(12, 24, 48, 0.8); }
.tk-chip-gold { border-color: var(--tk-gold); color: var(--tk-gold); background: var(--tk-gold-bg);
  letter-spacing: .06em; }
.tk-kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .8rem;
  margin: 0 0 1.1rem 0; }
@media (max-width: 1100px) { .tk-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 520px) { .tk-kpis { grid-template-columns: minmax(0, 1fr); } }
.tk-kpi { box-sizing: border-box; padding: .85rem 1rem; border-radius: 12px;
  border: 1px solid var(--ls-border); background: var(--ls-surface); border-top-width: 3px; }
.tk-kpi-teal { border-top-color: var(--ls-teal); }
.tk-kpi-gold { border-top-color: var(--tk-gold); }
.tk-kpi-blue { border-top-color: var(--ls-blue); }
.tk-kpi-navy { border-top-color: var(--ls-steel); }
.tk-kpi-label { font-size: .85rem; font-weight: 600; color: var(--ls-muted); }
.tk-kpi-val { font-size: 2rem; font-weight: 800; color: var(--ls-text); line-height: 1.15;
  margin-top: .1rem; }
.tk-kpi-note { font-size: .82rem; color: var(--ls-muted); margin-top: .2rem; line-height: 1.35; }
.tk-runs { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); gap: .8rem;
  align-items: stretch; margin: .5rem 0 1.1rem 0; }
@media (max-width: 820px) { .tk-runs { grid-template-columns: minmax(0, 1fr); } }
.tk-run { box-sizing: border-box; padding: .9rem 1rem; border-radius: 12px; min-width: 0;
  border: 1px solid var(--ls-border); background: var(--ls-surface); }
.tk-run-role { font-size: .78rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
  color: var(--ls-teal); }
.tk-run-id { font-size: .88rem; color: var(--ls-text); margin: .2rem 0 .5rem 0;
  overflow-wrap: anywhere; font-weight: 600; }
.tk-run dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: .25rem .8rem;
  margin: 0; font-size: .9rem; }
.tk-run dt { color: var(--ls-muted); }
.tk-run dd { margin: 0; color: var(--ls-text); overflow-wrap: anywhere; }
.tk-run-mid { display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: .4rem; padding: 0 .4rem; text-align: center; font-size: .82rem; color: var(--ls-muted); }
.tk-run-arrow { font-size: 1.6rem; color: var(--ls-teal); line-height: 1; }
@media (max-width: 820px) { .tk-run-arrow { transform: rotate(90deg); } }
.tk-split { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .9rem;
  margin: 0 0 1.1rem 0; }
@media (max-width: 900px) { .tk-split { grid-template-columns: minmax(0, 1fr); } }
.tk-panel { box-sizing: border-box; padding: .9rem 1rem; border-radius: 12px; min-width: 0;
  border: 1px solid var(--ls-border); background: var(--ls-surface); }
.tk-panel h4 { margin: 0 0 .15rem 0; font-size: 1.05rem; color: var(--ls-text); }
.tk-muted { font-size: .85rem; color: var(--ls-muted); margin-bottom: .6rem; line-height: 1.4; }
.tk-dist-row, .tk-cov-row { display: grid; grid-template-columns: minmax(7rem, 11rem) minmax(0, 1fr) auto;
  align-items: center; gap: .6rem; margin: .4rem 0; font-size: .9rem; color: var(--ls-text); }
.tk-cov-name small { color: var(--ls-muted); margin-left: .25rem; }
.tk-dist-n { font-size: .85rem; color: var(--ls-muted); white-space: nowrap; }
@media (max-width: 520px) {
  .tk-dist-row, .tk-cov-row { grid-template-columns: minmax(0, 1fr) auto; }
  .tk-dist-label, .tk-cov-name { grid-column: 1 / -1; }
}
.tk-panel progress { width: 100%; height: 10px; border: 0; border-radius: 99px; background: #1B2D4F;
  accent-color: var(--ls-teal); overflow: hidden; }
.tk-panel progress::-webkit-progress-bar { background: #1B2D4F; border-radius: 99px; }
.tk-panel progress::-webkit-progress-value { background: var(--ls-teal); border-radius: 99px; }
.tk-panel progress::-moz-progress-bar { background: var(--ls-teal); border-radius: 99px; }
.tk-panel .tk-chg progress::-webkit-progress-value { background: var(--ls-blue); }
.tk-panel .tk-chg progress::-moz-progress-bar { background: var(--ls-blue); }
.tk-panel .tk-rev progress::-webkit-progress-value { background: var(--tk-gold); }
.tk-panel .tk-rev progress::-moz-progress-bar { background: var(--tk-gold); }
.tk-panel .tk-gone progress::-webkit-progress-value { background: var(--tk-burgundy); }
.tk-panel .tk-gone progress::-moz-progress-bar { background: var(--tk-burgundy); }
.tk-panel .tk-same progress::-webkit-progress-value { background: var(--ls-steel); }
.tk-panel .tk-same progress::-moz-progress-bar { background: var(--ls-steel); }
.tk-table-wrap { margin: 0 0 1.1rem 0; border: 1px solid var(--ls-border); border-radius: 12px;
  overflow: hidden; background: var(--ls-surface); }
.tk-table { width: 100%; border-collapse: collapse; font-size: .93rem; }
.tk-table th { text-align: left; padding: .65rem .8rem; font-size: .78rem; letter-spacing: .08em;
  text-transform: uppercase; color: var(--ls-muted); background: var(--ls-surface-2);
  border-bottom: 1px solid var(--ls-border); }
.tk-table td { padding: .7rem .8rem; color: var(--ls-text); vertical-align: top;
  border-bottom: 1px solid rgba(39, 64, 107, 0.6); overflow-wrap: anywhere; }
.tk-table tr:last-child td { border-bottom: 0; }
.tk-table tbody tr:hover { background: rgba(63, 110, 153, 0.12); }
.tk-table tr.tk-rev td:first-child { box-shadow: inset 3px 0 0 var(--tk-gold); }
.tk-table tr.tk-chg td:first-child { box-shadow: inset 3px 0 0 var(--ls-blue); }
.tk-table tr.tk-gone td:first-child { box-shadow: inset 3px 0 0 var(--tk-burgundy); }
.tk-table tr.tk-new td:first-child { box-shadow: inset 3px 0 0 var(--ls-teal); }
.tk-badge { display: inline-block; white-space: nowrap; font-size: .78rem; font-weight: 700; padding: .18rem .55rem;
  border-radius: 999px; border: 1px solid var(--ls-steel); color: var(--ls-text); }
.tk-badge.tk-chg { border-color: var(--ls-blue); color: #9AD7F8; background: rgba(56, 189, 248, .10); }
.tk-badge.tk-rev { border-color: var(--tk-gold); color: var(--tk-gold); background: var(--tk-gold-bg); }
.tk-badge.tk-gone { border-color: var(--tk-burgundy); color: #F0A9B6; background: var(--tk-burgundy-bg); }
.tk-badge.tk-new { border-color: var(--ls-teal); color: var(--ls-teal); background: rgba(45, 212, 191, .08); }
@media (max-width: 820px) {
  .tk-table thead { position: absolute; left: -9999px; }
  .tk-table, .tk-table tbody, .tk-table tr, .tk-table td { display: block; width: 100%;
    box-sizing: border-box; }
  .tk-table tr { padding: .5rem 0; border-bottom: 1px solid var(--ls-border); }
  .tk-table td { border: 0; padding: .25rem .9rem; display: grid;
    grid-template-columns: 8.5rem minmax(0, 1fr); gap: .5rem; }
  .tk-table td::before { content: attr(data-label); font-size: .78rem; font-weight: 700;
    color: var(--ls-muted); text-transform: uppercase; letter-spacing: .06em; }
}
.tk-why { padding: .6rem .8rem; border-radius: 10px; border: 1px solid var(--ls-border);
  background: rgba(17, 34, 68, 0.7); color: var(--ls-text); font-size: .93rem; line-height: 1.5;
  margin-bottom: .6rem; }
.tk-why.tk-rev { border-color: var(--tk-gold); background: var(--tk-gold-bg); }
.tk-why.tk-chg { border-color: var(--ls-blue); background: rgba(56, 189, 248, .08); }
.tk-why.tk-gone { border-color: var(--tk-burgundy); background: var(--tk-burgundy-bg); }
.tk-change { padding: .6rem .8rem; border-radius: 10px; margin-bottom: .5rem;
  border: 1px solid var(--ls-border); background: var(--ls-surface); font-size: .92rem; }
.tk-change-top { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; }
.tk-sides { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .6rem;
  margin-top: .5rem; color: var(--ls-text); overflow-wrap: anywhere; }
@media (max-width: 640px) { .tk-sides { grid-template-columns: minmax(0, 1fr); } }
.tk-side-role { font-size: .74rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  color: var(--ls-muted); }
.tk-urls { margin: .5rem 0 0 1.1rem; padding: 0; }
.tk-urls li { margin: .15rem 0; overflow-wrap: anywhere; }
.tk-url { color: var(--ls-blue); overflow-wrap: anywhere; word-break: break-word; }
.tk-limits { margin: .25rem 0 0 1.1rem; padding: 0; color: var(--ls-text); }
.tk-section-title { margin: 1.3rem 0 .4rem 0; font-size: 1.25rem; font-weight: 700;
  color: var(--ls-text); }
@media (max-width: 640px) {
  .tk-hero { padding: .9rem 1rem; }
  .tk-hero h2 { font-size: 1.4rem; }
  .tk-kpi-val { font-size: 1.7rem; }
}
</style>
"""


def inject_cockpit_theme() -> None:
    """Inject the Research Intelligence Cockpit styles (only used by the cockpit view)."""
    st.markdown(COCKPIT_CSS, unsafe_allow_html=True)


def inject_tracking_theme() -> None:
    """Weekly Tracking dashboard styles (idempotent: the markup is static)."""
    st.markdown(TRACKING_CSS, unsafe_allow_html=True)


def inject_theme() -> None:
    """Inject the single CSS block. Call once per script run, before building tabs."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, tagline: str = "", demo: bool = False) -> None:
    """Brand band: logo mark, product title, subtitle and tagline (and the demo indicator)."""
    tag = f'<div class="ls-hero-tag">{tagline}</div>' if tagline else ""
    badge = demo_badge() if demo else ""
    st.markdown(
        f'<div class="ls-hero">{logo_html()}<div class="ls-hero-text">'
        f'<h1>{title}</h1><div class="ls-hero-sub">{subtitle}</div>{tag}</div>{badge}</div>',
        unsafe_allow_html=True,
    )


def section(title: str, caption: str = "") -> None:
    """Section heading with optional caption."""
    html = f'<div class="ls-head"><div class="ls-section">{title}</div>'
    if caption:
        html += f'<div class="ls-caption">{caption}</div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)


def pill(text: str, kind: str = "") -> str:
    """Return HTML for a status pill; kind is '', 'ok', 'warn' or 'idle'."""
    cls = {"ok": " ls-pill-ok", "warn": " ls-pill-warn", "idle": " ls-pill-idle"}.get(kind, "")
    return f'<span class="ls-pill{cls}">{text}</span>'


_ICON_BAN = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
    '<path d="M5.6 5.6l12.8 12.8"/></svg>'
)
_ICON_BOOK = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M3 5.5C5 4.5 8.5 4.5 12 6c3.5-1.5 7-1.5 9-.5V19c-2-1-5.5-1-9 .5-3.5-1.5-7-1.5-9-.5z"/>'
    '<path d="M12 6v13.5"/></svg>'
)
_ICON_LIST = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v3H9z"/>'
    '<path d="M9 11h6M9 15h6"/></svg>'
)
_ICON_CHECK = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" '
    'r="9"/><path d="M7.5 12.5l3 3 6-6.5"/></svg>'
)

DEMO_BADGE_LINES: tuple[str, str] = ("Showcasing real saved results", "No API usage")
DEMO_BANNER_TITLE = "Public Demo: Live research and deck generation are disabled on this deployment."
DEMO_BANNER_TEXT = (
    "This demo showcases saved research runs only. No new research is executed and no API "
    "calls are made."
)
DEMO_GUIDE_TITLE = "Public Demo: Live research is disabled. Pick a saved run below."
DEMO_GUIDE_TEXT = (
    "Explore real research results, replay the agent workflows and download the reports and "
    "pitch decks."
)
DEMO_RESEARCH_NOTE = "Public demo: live research is disabled. Pick a saved run below."
DEMO_DECK_NOTE = (
    "Public demo: new pitch deck generation is disabled. Download the existing deck below."
)


def demo_badge() -> str:
    """Compact header indicator (HTML); callers show it only in demo mode."""
    return (
        f'<div class="ls-demo-badge">{_ICON_BOOK}<div><div class="ls-demo-badge-title">'
        f'DEMO MODE</div><div class="ls-demo-badge-line">{DEMO_BADGE_LINES[0]}</div>'
        f'<div class="ls-demo-badge-line">{DEMO_BADGE_LINES[1]}</div></div></div>'
    )


def demo_banner() -> None:
    """Announcement banner shown under the header in demo mode."""
    st.markdown(
        '<div class="ls-demo-banner"><div class="ls-demo-banner-main">'
        f'{_ICON_BAN}<div><div class="ls-demo-banner-title">{DEMO_BANNER_TITLE}</div>'
        f'<div class="ls-demo-banner-text">{DEMO_BANNER_TEXT}</div></div></div>'
        '<div class="ls-demo-chips">'
        f'<span class="ls-demo-chip">{_ICON_BAN}<span>Live research<br>disabled</span></span>'
        f'<span class="ls-demo-chip">{_ICON_BAN}<span>New pitch deck<br>generation disabled'
        "</span></span>"
        f'<span class="ls-demo-chip ok">{_ICON_CHECK}<span>Explore saved runs<br>'
        "download reports</span></span></div></div>",
        unsafe_allow_html=True,
    )


def demo_guide() -> None:
    """Blue guidance banner at the top of the Research Workspace in demo mode."""
    st.markdown(
        f'<div class="ls-demo-guide">{_ICON_LIST}<div>'
        f'<div class="ls-demo-guide-title">{DEMO_GUIDE_TITLE}</div>'
        f'<div class="ls-demo-guide-text">{DEMO_GUIDE_TEXT}</div></div></div>',
        unsafe_allow_html=True,
    )


def demo_note(text: str) -> None:
    """Compact high-contrast notice under a disabled action in demo mode."""
    st.markdown(
        f'<div class="ls-demo-note" role="note">{_ICON_BAN}<span>{text}</span></div>',
        unsafe_allow_html=True,
    )
