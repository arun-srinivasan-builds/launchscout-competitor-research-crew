"""Render a `DeckSpec` as a premium, fully editable six-slide investor presentation (V3).

Slides are composed from native shapes, text boxes, connectors and progress bars (no flattened
images); the only picture is the approved LS logo. Layout is content-agnostic: numbers and text
come from the saved research (`DeckSource`) and the validated `DeckSpec`; nothing is hardcoded
to one business idea, and missing evidence is shown as missing, never filled in. Verified
findings, recommendations, assumptions and unknowns keep distinct labels.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches

from launchscout.exports.pptx_components import (
    BLUE,
    BLUE_LIGHT,
    BORDER,
    BURGUNDY,
    BURGUNDY_LIGHT,
    CONTENT_BOTTOM,
    CONTENT_W,
    CREAM,
    FOOTER_TOP,
    GAP,
    GOLD,
    GOLD_LIGHT,
    HEAD_FONT,
    INK,
    LINE_SPACING,
    MARGIN_X,
    MUTED,
    PAPER,
    SERIF_EM_FACTOR,
    SLIDE_H,
    SLIDE_W,
    TEAL,
    TEAL_LIGHT,
    TEAL_ON_INK,
    WHITE,
    Para,
    arrow,
    badge,
    bar,
    box,
    chip,
    chip_width,
    estimate_lines,
    needed_height_in,
    panel,
)
from launchscout.exports.pptx_components import text as text_box
from launchscout.schemas import Competitor, DeckSpec, SlideSpec

if TYPE_CHECKING:
    from launchscout.deck import DeckSource

LOGO_FILE = Path(__file__).resolve().parent.parent.parent / "static" / "ls_logo_transparent.png"
LOGO_ASPECT = 691 / 623
GATE_MIN = 3  # mirrors validation.evaluate_gate (3 evidence-backed competitors, 3 verified prices)
SLIDE_NAMES = (
    "Problem & Opportunity",
    "Market Landscape",
    "Customer Insights",
    "Solution & Differentiation",
    "Go-to-Market Strategy",
    "Financials & Roadmap",
)
_AMOUNT = re.compile(r"(₹|Rs\.?|INR|\$|USD|€|EUR)\s?(\d[\d,]*(?:\.\d+)?)", re.I)
_WEEK = re.compile(r"^\s*week\s*(\d+)\s*[:\-–—]\s*(.+)$", re.I | re.S)
_URL = re.compile(r"https?://\S+")
_FOOTER_NAMES = ("Footer", "Footer rule", "Slide number")
_HEADER_BOTTOM = 1.08


# ----------------------------------------------------------------------------- small helpers
def _short(value: str, limit: int) -> str:
    value = " ".join((value or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:.- ") + "…"


def _host(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0]


def _currency(symbol: str) -> str:
    return "₹" if symbol.upper() in ("INR", "RS", "RS.") else symbol


def _sentences(value: str) -> list[str]:
    parts = [s.strip().rstrip(";") for s in re.split(r"(?<=[.;])\s+", value or "")]
    return [p for p in parts if p]


def _unlabel(value: str) -> str:
    """Drop a leading 'Recommendation:' (the tag already says it) and wrapping quotes."""
    cleaned = re.sub(r"^\s*recommendation\s*:\s*", "", value or "", flags=re.I).strip()
    cleaned = cleaned.strip("\"'“”‘’ ")
    return cleaned[:1].upper() + cleaned[1:]


def _plain(value: str) -> str:
    """Text without bare URLs (they stay in the source list and the notes)."""
    no_urls = _URL.sub("", value or "")
    no_urls = re.sub(r"\s*;\s*;", ";", no_urls)
    return " ".join(no_urls.replace(" ;", ";").split()).strip(" ;,")


def _bullets(items: list[str], size: float = 12.5, color=INK) -> list[Para]:
    return [Para(i, size, color, bullet=True, after=4) for i in items]


class Ctx:
    """Read-only facts for layout (all derived from the saved run and the stored deck)."""

    def __init__(self, deck: DeckSpec, source: DeckSource, generated_on: date) -> None:
        self.deck, self.source, self.generated_on = deck, source, generated_on
        self.comps: list[Competitor] = source.competitors.competitors
        self.n_evidence = sum(1 for c in self.comps if c.evidence_urls)
        self.n_verified = source.verified_prices
        self.unverified = [c.name for c in self.comps if c.price.status != "verified"]

    @property
    def status_label(self) -> str:
        return "PARTIAL EVIDENCE" if self.source.partial else "VALIDATED REPORT"


# ----------------------------------------------------------------------------- page chrome
class Page:
    """One slide: branded header, optional label banner, sources strip and footer."""

    def __init__(self, prs, ctx: Ctx, index: int, spec: SlideSpec) -> None:
        self.ctx, self.index, self.spec = ctx, index, spec
        self.full: list[str] = []  # full text of anything shortened to fit (kept in the notes)
        self.slide = prs.slides.add_slide(prs.slide_layouts[6])
        fill = self.slide.background.fill
        fill.solid()
        fill.fore_color.rgb = CREAM
        self._header()
        self.top = self._banner()
        self.bottom = self._sources()

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def text(self, x, y, w, h, paras, **kw):
        items = [paras] if isinstance(paras, Para) else list(paras)
        originals = [p.text for p in items]
        shape, fit = text_box(self.slide, x, y, w, h, items, **kw)
        if fit.truncated:
            self.full.extend(o for o, p in zip(originals, fit.paras, strict=True) if o != p.text)
        return shape, fit

    def _header(self) -> None:
        s, ctx = self.slide, self.ctx
        box(s, MARGIN_X, 0.22, 3.3, 0.76, fill=INK, name="Brand block")
        box(s, MARGIN_X + 0.1, 0.31, 0.58, 0.58, fill=WHITE, name="LS logo tile")
        pic_h = 0.46
        pic_w = pic_h * LOGO_ASPECT
        pic = s.shapes.add_picture(
            str(LOGO_FILE),
            Inches(MARGIN_X + 0.1 + (0.58 - pic_w) / 2),
            Inches(0.37),
            height=Inches(pic_h),
        )
        pic.name = "LS logo"
        pic._element.nvPicPr.cNvPr.set("descr", "LaunchScout LS logo")
        text_box(
            s, MARGIN_X + 0.82, 0.25, 2.4, 0.37,
            Para("LaunchScout", 18, WHITE, bold=True, font=HEAD_FONT, after=0),
            pad=0.02, name="Brand name",
        )
        text_box(
            s, MARGIN_X + 0.82, 0.63, 2.4, 0.28,
            Para("Competitor Research Crew", 11, TEAL_ON_INK, bold=True, after=0),
            pad=0.02, name="Brand tagline",
        )
        label = ctx.status_label
        width = chip_width(label, 11)
        status_fill = GOLD_LIGHT if ctx.source.partial else TEAL_LIGHT
        status_color = GOLD if ctx.source.partial else TEAL
        chip(
            s, SLIDE_W - MARGIN_X - width, 0.36, label, status_fill, status_color,
            size=11, h=0.34, name="Evidence status", line=status_color,
        )
        title_x = MARGIN_X + 3.3 + 0.3
        text_box(
            s, title_x, 0.2, 0.8, 0.5,
            Para(f"{self.index:02d}", 26, GOLD, bold=True, font=HEAD_FONT, after=0),
            pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name="Slide index",
        )
        title_w = SLIDE_W - MARGIN_X - width - 0.25 - (title_x + 0.8)
        text_box(
            s, title_x + 0.8, 0.2, title_w, 0.5,
            Para(SLIDE_NAMES[self.index - 1], 26, BURGUNDY, bold=True, font=HEAD_FONT, after=0),
            pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name="Title",
        )
        sub = f"{self.spec.title}  ·  {ctx.source.input.idea}  ·  {ctx.source.input.city}"
        text_box(
            s, title_x + 0.8, 0.7, title_w, 0.28,
            Para(_short(sub, 110), 12, MUTED, after=0), pad=0.02, name="Subtitle",
        )
        box(s, MARGIN_X, _HEADER_BOTTOM - 0.04, CONTENT_W, 0.025, fill=GOLD, round_=False,
            name="Header rule")

    def _banner(self) -> float:
        top = _HEADER_BOTTOM + 0.1
        if self.spec.labels:
            paras = [Para("   ·   ".join(self.spec.labels), 11.5, BURGUNDY, bold=True, after=0)]
            h = needed_height_in(paras, CONTENT_W, pad=0.12) + 0.04
            text_box(
                self.slide, MARGIN_X, top, CONTENT_W, h, paras,
                fill=BURGUNDY_LIGHT, line=BURGUNDY, pad=0.12, anchor=MSO_ANCHOR.MIDDLE,
                name="Labels",
            )
            top += h + 0.12
        return top

    def _sources(self) -> float:
        """Sources strip above the footer; returns the bottom of the free content area."""
        refs = []
        for ref in self.spec.source_refs:
            label = _host(ref) if ref.startswith("http") else ref
            if label and label not in refs:
                refs.append(label)
        shown = " · ".join(refs[:6]) + (f" · +{len(refs) - 6} more" if len(refs) > 6 else "")
        line = f"Sources: {shown}" if refs else "Sources: none cited for this slide"
        y = CONTENT_BOTTOM - 0.3
        text_box(
            self.slide, MARGIN_X, y, CONTENT_W, 0.3,
            Para(_short(line, 190), 10.5, MUTED, after=0), pad=0.02,
            anchor=MSO_ANCHOR.MIDDLE, name="Sources",
        )
        return y - 0.08

    def finish(self, extra: list[str]) -> None:
        s, ctx = self.slide, self.ctx
        arrow(s, MARGIN_X, FOOTER_TOP, SLIDE_W - MARGIN_X, FOOTER_TOP, BORDER, width_pt=1.0,
              head=False, name="Footer rule")
        footer = (
            f"LaunchScout  |  {SLIDE_NAMES[self.index - 1]}  |  "
            f"{ctx.source.input.idea}, {ctx.source.input.city}  |  "
            f"{'Partial evidence' if ctx.source.partial else 'Validated report'}  |  "
            f"run {ctx.source.run_id}"
        )
        text_box(
            s, MARGIN_X, FOOTER_TOP + 0.04, CONTENT_W - 1.2, 0.3,
            Para(_short(footer, 170), 10, MUTED, after=0), pad=0.02, name="Footer",
        )
        text_box(
            s, SLIDE_W - MARGIN_X - 1.1, FOOTER_TOP + 0.03, 1.1, 0.3,
            Para(f"{self.index:02d} / 06", 11, BURGUNDY, bold=True, align=PP_ALIGN.RIGHT,
                 after=0),
            pad=0.02, name="Slide number",
        )
        _notes(s, self.spec, extra + (
            ["Full text of items shortened on the slide:"] + [f"  {t}" for t in self.full]
            if self.full else []
        ))


def _notes(slide, spec: SlideSpec, extra: list[str]) -> None:
    parts: list[str] = []
    if spec.notes.strip():
        parts.append(spec.notes.strip())
    if spec.bullets:
        parts.append("Validated slide text:\n" + "\n".join(f"- {b}" for b in spec.bullets))
    if extra:
        parts.append("Visual detail:\n" + "\n".join(f"- {line}" for line in extra))
    if spec.source_refs:
        parts.append("Sources:\n" + "\n".join(spec.source_refs))
    if spec.labels:
        parts.append("Labels: " + "; ".join(spec.labels))
    slide.notes_slide.notes_text_frame.text = "\n\n".join(parts)


def _kv(
    page: Page, x: float, y: float, w: float, label: str, value: str, size: float = 13
) -> float:
    """A label/value pair; returns the y after it."""
    paras = [
        Para(label.upper(), 10.5, MUTED, bold=True, after=1),
        Para(value, size, INK, bold=True, after=0),
    ]
    h = needed_height_in(paras, w, pad=0.02)
    page.text(x, y, w, h, paras, pad=0.02, name=f"Fact: {label}")
    return y + h + 0.08


def _rule(page: Page, x: float, y: float, w: float) -> None:
    box(page.slide, x, y, w, 0.015, fill=BORDER, round_=False, name="Divider")


# ----------------------------------------------------------------------------- slide 1
def _slide_problem(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    src, inp = ctx.source, ctx.source.input
    top, height = page.top, page.height
    wa, wb = 3.9, 4.4
    wc = CONTENT_W - wa - wb - 2 * GAP
    xa, xb, xc = MARGIN_X, MARGIN_X + wa + GAP, MARGIN_X + wa + wb + 2 * GAP
    notes: list[str] = []

    # A: the opportunity
    y = panel(s, xa, top, wa, height, "The opportunity", accent=BURGUNDY)
    paras = [Para(inp.idea, 22, INK, bold=True, font=HEAD_FONT, after=0)]
    h = needed_height_in(paras, wa - 0.4)
    page.text(xa + 0.2, y, wa - 0.4, h, paras, pad=0.02, name="Business idea")
    y += h + 0.02
    page.text(xa + 0.2, y, wa - 0.4, 0.34, Para(f"in {inp.city}", 15, TEAL, bold=True, after=0),
              pad=0.02, name="City")
    y += 0.46
    _rule(page, xa + 0.2, y, wa - 0.4)
    y = _kv(page, xa + 0.2, y + 0.1, wa - 0.4, "Target customer", inp.target_customer, 15) + 0.04
    _rule(page, xa + 0.2, y, wa - 0.4)
    page.text(xa + 0.2, y + 0.08, wa - 0.4, 0.28,
              Para("RESEARCH SUMMARY", 10.5, MUTED, bold=True, after=0), pad=0.02,
              name="Summary heading")
    y += 0.4
    page.text(xa + 0.2, y, wa - 0.4, top + height - y - 0.12, _bullets(spec.bullets, 14),
              pad=0.02, name="Research summary")

    # B: customer -> market -> gap
    y = panel(s, xb, top, wb, height, "From customer to opportunity", accent=BLUE)
    area = top + height - y - 0.12
    gap_h = 0.32
    unit = (area - 2 * gap_h) / 3.0
    weights = (0.6, 1.0, 1.4)
    channels = sorted({ch for c in ctx.comps for ch in c.channels})
    market = (
        f"{len(ctx.comps)} competitor(s) researched; {ctx.n_evidence} with public evidence URLs; "
        f"{ctx.n_verified} verified price(s)."
        + (f" Channels seen: {', '.join(channels[:4])}." if channels else "")
    )
    gap_text = _short(_plain(src.strategy.market_gap), 300) or (
        "No market-gap statement was recorded in the research."
    )
    nodes = (
        ("TARGET CUSTOMER", f"{inp.target_customer} in {inp.city}.", TEAL_LIGHT, TEAL),
        ("OBSERVED IN THE MARKET", market, BLUE_LIGHT, BLUE),
        ("RESEARCH-VISIBLE GAP (INFERENCE, NOT A MARKET SIZE)", gap_text, BURGUNDY_LIGHT,
         BURGUNDY),
    )
    ny = y
    for i, (label, body, fill, accent) in enumerate(nodes, 1):
        node_h = unit * weights[i - 1]
        box(s, xb + 0.2, ny, wb - 0.4, node_h, fill=fill, line=accent, name=f"Node {i}")
        page.text(
            xb + 0.3, ny + 0.05, wb - 0.6, node_h - 0.1,
            [Para(label, 10.5, accent, bold=True, after=2), Para(body, 12.5, INK, after=0)],
            pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name=f"Node {i} text",
        )
        if i < len(nodes):
            arrow(s, xb + wb / 2, ny + node_h, xb + wb / 2, ny + node_h + gap_h, accent,
                  width_pt=2.5, name=f"Flow arrow {i}")
        ny += node_h + gap_h
    notes.append("Flow: target customer -> observed market -> research-visible gap")

    # C: scope and evidence status
    y = panel(s, xc, top, wc, height, "Research scope & evidence", accent=TEAL)
    mode = getattr(inp.mode, "value", inp.mode)
    half = (wc - 0.4 - 0.1) / 2
    facts = (
        ("Competitors", str(len(ctx.comps))),
        ("Sources reviewed", str(len(src.evidence_urls)) if src.evidence_urls else "none"),
        ("Report status", "Partial" if src.partial else "Validated"),
        ("Research mode", str(mode).title()),
    )
    for row in (0, 2):
        ny = y
        for col in (0, 1):
            label, value = facts[row + col]
            ny = max(ny, _kv(page, xc + 0.2 + col * (half + 0.1), y, half, label, value, 13))
        y = ny
    for label, have in (("Competitors with evidence", ctx.n_evidence),
                        ("Verified competitor prices", ctx.n_verified)):
        page.text(xc + 0.2, y, wc - 0.4, 0.26,
                  Para(f"{label}: {have} of {GATE_MIN} required", 11, INK, bold=True, after=0),
                  pad=0.02, name=f"Gauge label: {label}")
        bar(s, xc + 0.2, y + 0.3, wc - 0.4, 0.14, have / GATE_MIN,
            TEAL if have >= GATE_MIN else GOLD, name=f"Gauge: {label}")
        y += 0.56
    if src.partial and src.acceptance_reasons:
        page.text(xc + 0.2, y, wc - 0.4, 0.26,
                  Para("WHY THE REPORT IS PARTIAL", 10.5, MUTED, bold=True, after=0), pad=0.02,
                  name="Partial heading")
        reasons = [_short(r, 150) for r in src.acceptance_reasons[:3]]
        page.text(xc + 0.2, y + 0.28, wc - 0.4, top + height - y - 0.4,
                  _bullets(reasons, 11.5, INK), pad=0.02, name="Acceptance gaps")
    page.finish(notes)


# ----------------------------------------------------------------------------- slide 2
def _slide_market(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    top, height = page.top, page.height
    lw = 8.3
    rw = CONTENT_W - lw - GAP
    xr = MARGIN_X + lw + GAP
    cols = (1.5, 2.8, 1.65, 2.35)
    heads = ("COMPETITOR", "OFFER & POSITIONING", "CHANNELS", "PRICE")
    notes: list[str] = []

    box(s, MARGIN_X, top, lw, height, fill=PAPER, line=BORDER, name="Matrix card")
    x = MARGIN_X
    for head, w in zip(heads, cols, strict=True):
        page.text(x + 0.12, top + 0.08, w - 0.12, 0.3,
                  Para(head, 10.5, BURGUNDY, bold=True, after=0), pad=0.02,
                  name=f"Matrix head: {head.title()}")
        x += w
    comps = ctx.comps
    area_top = top + 0.46
    area = top + height - area_top - 0.1
    n = max(1, len(comps))
    row_h = min(2.4, (area - 0.1 * (n - 1)) / n)
    if not comps:
        page.text(MARGIN_X + 0.2, area_top, lw - 0.4, 0.8,
                  Para("No competitor met the evidence threshold in the saved research.", 13,
                       MUTED, after=0), pad=0.02, name="No competitors")
    y = area_top
    for comp in comps:
        box(s, MARGIN_X + 0.1, y, lw - 0.2, row_h, fill=CREAM, line=BORDER,
            name=f"Competitor: {comp.name}")
        x = MARGIN_X
        tight = row_h < 1.0
        paras = [Para(comp.name, 12.5 if tight else 15, INK, bold=True, after=1)]
        if not tight:
            paras.append(Para(_host(comp.url), 11, MUTED, after=0))
        page.text(x + 0.18, y + 0.06, cols[0] - 0.22, row_h - 0.12, paras, pad=0.02,
                  name=f"Name: {comp.name}")
        x += cols[0]
        offer_paras = [
            Para(_plain(comp.offer) or "Offer not recorded.", 11 if tight else 13, INK, after=6)
        ]
        if comp.location_relevance and row_h >= 1.4:
            offer_paras.append(Para("Local relevance: " + _plain(comp.location_relevance), 11,
                                    MUTED, after=0))
        page.text(x + 0.08, y + 0.06, cols[1] - 0.16, row_h - 0.12, offer_paras,
                  pad=0.02, name=f"Offer: {comp.name}")
        x += cols[1]
        chans = comp.channels[: 2 if tight else 3] or ["Not recorded"]
        page.text(x + 0.08, y + 0.06, cols[2] - 0.12, row_h - 0.12,
                  _bullets(chans, 11 if tight else 12),
                  pad=0.02, name=f"Channels: {comp.name}")
        x += cols[2]
        price = comp.price
        verified = price.status == "verified" and price.amount is not None
        label = (
            f"{_currency(price.currency or '')}{price.amount:g}" if verified else "PRICE UNKNOWN"
        )
        chip(s, x + 0.08, y + 0.1, label, TEAL_LIGHT if verified else GOLD_LIGHT,
             TEAL if verified else GOLD, size=11, h=0.34, name=f"Price: {comp.name}",
             line=TEAL if verified else GOLD)
        sub = (
            " ".join(p for p in (price.unit, price.pack_size) if p) or "verified with evidence"
            if verified
            else "Not verified"
        )
        compact = row_h < 1.25
        urls = f"{len(comp.evidence_urls)} source URL(s)"
        if compact:
            note_paras = [Para(f"{sub} · {urls}", 10.5, MUTED, after=0)]
        else:
            note_paras = [Para(sub, 11, MUTED, bold=True, after=2), Para(urls, 11, MUTED, after=4)]
            if comp.unknowns:
                note_paras.append(Para("Unknown: " + _short(_plain(comp.unknowns[0]), 240), 10.5,
                                       MUTED, after=0))
        if row_h >= 0.9:
            page.text(x + 0.08, y + 0.5, cols[3] - 0.26, row_h - 0.56, note_paras,
                      pad=0.02, name=f"Price note: {comp.name}")
        y += row_h + 0.1

    # right: findings and coverage
    top_h = height * 0.56
    y = panel(s, xr, top, rw, top_h, "Competitive findings", accent=BURGUNDY)
    page.text(xr + 0.2, y, rw - 0.35, top + top_h - y - 0.1, _bullets(spec.bullets, 13.5),
              pad=0.02, name="Findings")
    cy = top + top_h + GAP
    ch = top + height - cy
    y = panel(s, xr, cy, rw, ch, "Evidence coverage", accent=TEAL)
    peak = max([len(c.evidence_urls) for c in comps] + [1])
    each = min(0.62, (cy + ch - y - 0.1) / max(1, len(comps)))
    if each < 0.34:  # many competitors: one compact list instead of a bar per competitor
        joined = "  ·  ".join(f"{c.name}: {len(c.evidence_urls)}" for c in comps)
        page.text(xr + 0.2, y, rw - 0.4, cy + ch - y - 0.1,
                  [Para("Source URLs per competitor", 10.5, MUTED, bold=True, after=3),
                   Para(joined, 11, INK, after=0)], pad=0.02, name="Coverage list")
    else:
        for comp in comps:
            page.text(xr + 0.2, y, rw - 0.4, 0.26,
                      Para(f"{comp.name}: {len(comp.evidence_urls)} source URL(s)", 11, INK,
                           bold=True, after=0), pad=0.02,
                      name=f"Coverage label: {comp.name}")
            bar(s, xr + 0.2, y + 0.3, rw - 0.4, 0.14, len(comp.evidence_urls) / peak, TEAL,
                name=f"Coverage: {comp.name}")
            y += each
    notes.append("Matrix columns: competitor, offer and positioning, channels, price status")
    page.finish(notes)


# ----------------------------------------------------------------------------- slide 3
def _slide_customers(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    top, height = page.top, page.height
    findings = list(ctx.source.reviews.findings)
    notes: list[str] = []

    by_comp: dict[str, list] = {}
    for f in findings:
        by_comp.setdefault(f.competitor, []).append(f)
    shown: list = []
    for rank in range(4):  # round-robin so every researched competitor is represented
        for group in by_comp.values():
            if rank < len(group) and len(shown) < 4:
                shown.append(group[rank])

    top_h = height * 0.55
    n = max(1, len(shown))
    card_w = (CONTENT_W - GAP * (n - 1)) / n
    if not shown:
        y = panel(s, MARGIN_X, top, CONTENT_W, top_h, "Customer feedback retrieved",
                  accent=BURGUNDY)
        page.text(MARGIN_X + 0.2, y, CONTENT_W - 0.4, 1.0,
                  Para("No customer feedback was retrieved in the saved research. Customer "
                       "needs and pain points are therefore unverified.", 13, MUTED, after=0),
                  pad=0.02, name="No feedback")
    for i, f in enumerate(shown):
        x = MARGIN_X + i * (card_w + GAP)
        accent = TEAL if f.kind == "praise" else BURGUNDY
        box(s, x, top, card_w, top_h, fill=PAPER, line=BORDER, name=f"Insight card {i + 1}")
        box(s, x, top + 0.1, 0.06, top_h - 0.2, fill=accent, round_=False, name="Accent")
        chip(s, x + 0.2, top + 0.12, f.competitor.upper()[:22], TEAL_LIGHT if f.kind == "praise"
             else BURGUNDY_LIGHT, accent, size=10.5, h=0.32, name=f"Source: {f.competitor}")
        basis = {"quoted": "Quoted", "reported": "Reported", "inferred": "Inferred"}[f.basis]
        origin = f"{basis} · {_host(f.source_url)}" if f.source_url else basis
        page.text(x + 0.2, top + 0.5, card_w - 0.35, 0.46,
                  [Para(origin, 10.5, MUTED, bold=True, after=0),
                   Para(f"{f.kind.title()} · not independently verified", 10.5, MUTED,
                        after=0)],
                  pad=0.02, name=f"Provenance {i + 1}")
        page.text(x + 0.2, top + 1.0, card_w - 0.35, top_h - 1.12,
                  Para(f.text, 13, INK, after=0, italic=True), pad=0.02,
                  name=f"Quote {i + 1}")
    if len(findings) > len(shown):
        notes.append(f"{len(findings) - len(shown)} more finding(s) are in the saved report")

    # bottom row: counts, pain points and opportunities, limits of the data
    by = top + top_h + GAP
    bh = top + height - by
    w1 = 3.6
    w2 = (CONTENT_W - w1 - 2 * GAP) * 0.5
    w3 = CONTENT_W - w1 - w2 - 2 * GAP
    x1, x2, x3 = MARGIN_X, MARGIN_X + w1 + GAP, MARGIN_X + w1 + w2 + 2 * GAP

    praise = sum(1 for f in findings if f.kind == "praise")
    complaint = len(findings) - praise
    y = panel(s, x1, by, w1, bh, "Findings retrieved", accent=TEAL)
    peak = max(praise, complaint, 1)
    for label, count, color in (("Praise", praise, TEAL), ("Complaints", complaint, BURGUNDY)):
        page.text(x1 + 0.2, y, w1 - 0.4, 0.26,
                  Para(f"{label}: {count}", 12, INK, bold=True, after=0), pad=0.02,
                  name=f"Count label: {label}")
        bar(s, x1 + 0.2, y + 0.3, w1 - 0.4, 0.15, count / peak, color, name=f"Count: {label}")
        y += 0.56

    y = panel(s, x2, by, w2, bh, "Pain points & opportunities", accent=BURGUNDY)
    page.text(x2 + 0.2, y, w2 - 0.35, by + bh - y - 0.1, _bullets(spec.bullets, 13),
              pad=0.02, name="Pain points")

    y = panel(s, x3, by, w3, bh, "Limits of the customer data", accent=GOLD)
    limits = [_short(_plain(g), 260) for g in ctx.source.reviews.gaps[:3]] or [
        "No customer-data gaps were recorded."
    ]
    page.text(x3 + 0.2, y, w3 - 0.35, by + bh - y - 0.1, _bullets(limits, 12.5),
              pad=0.02, name="Limitations")
    page.finish(notes)


# ----------------------------------------------------------------------------- slide 4
def _slide_solution(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    st = ctx.source.strategy
    top, height = page.top, page.height
    notes: list[str] = []

    hero_h = 0.95
    box(s, MARGIN_X, top, CONTENT_W, hero_h, fill=BURGUNDY_LIGHT, line=BURGUNDY,
        name="Value proposition")
    chip(s, MARGIN_X + 0.2, top + hero_h / 2 - 0.16, "RECOMMENDATION", WHITE, BURGUNDY, size=11,
         h=0.32, name="Positioning tag", line=BURGUNDY)
    x0 = MARGIN_X + 0.2 + chip_width("RECOMMENDATION", 11) + 0.25
    positioning = _unlabel(st.positioning_line) or _unlabel(st.recommended_offer) or (
        "No positioning statement was recorded."
    )
    page.text(x0, top + 0.08, SLIDE_W - MARGIN_X - 0.2 - x0, hero_h - 0.16,
              Para(positioning, 19, INK, bold=True, font=HEAD_FONT, after=0, italic=True),
              pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name="Value proposition text")

    status_h = 1.0
    cols_y = top + hero_h + GAP
    cols_h = top + height - cols_y - status_h - GAP
    cw = (CONTENT_W - 2 * GAP) / 3

    # observed
    y = panel(s, MARGIN_X, cols_y, cw, cols_h, "What the research shows", accent=BLUE)
    observed = []
    for c in ctx.comps:
        row = next((r for r in st.comparison_matrix if r.get("competitor") == c.name), {})
        observed.append(f"{c.name}: {_short(_plain(row.get('strength') or c.offer), 260)}")
    page.text(MARGIN_X + 0.2, y, cw - 0.35, cols_y + cols_h - y - 0.1,
              _bullets(observed or ["No competitor findings were recorded."], 13),
              pad=0.02, name="Observed")
    # differentiation
    x2 = MARGIN_X + cw + GAP
    y = panel(s, x2, cols_y, cw, cols_h, "Differentiation opportunities", accent=TEAL)
    page.text(x2 + 0.2, y, cw - 0.35, cols_y + cols_h - y - 0.1, _bullets(spec.bullets, 13.5),
              pad=0.02, name="Opportunities")
    # recommendation
    x3 = x2 + cw + GAP
    y = panel(s, x3, cols_y, cw, cols_h, "Recommended offer", accent=BURGUNDY)
    why = " ".join(_sentences(_plain(st.rationale))[:2])
    paras = [Para(_unlabel(st.recommended_offer) or "No offer recommendation was recorded.", 13.5,
                  INK, bold=True, after=8)]
    if why:
        paras.append(Para("Why: " + why, 12, MUTED, after=0))
    page.text(x3 + 0.2, y, cw - 0.35, cols_y + cols_h - y - 0.1, paras, pad=0.02,
              name="Recommended offer")

    # status row: what is verified, unverified, assumed
    sy = cols_y + cols_h + GAP
    unverified = ", ".join(ctx.unverified) if ctx.unverified else "none"
    cards = (
        ("VERIFIED", f"{ctx.n_evidence} of {len(ctx.comps)} competitors",
         "have public evidence URLs for their offer and channels.", TEAL, TEAL_LIGHT),
        ("UNVERIFIED", f"{len(ctx.unverified)} competitor price(s)",
         f"are unknown or not verified: {unverified}.", GOLD, GOLD_LIGHT),
        ("ASSUMPTION", "The gap is an inference",
         "drawn from this research; it is not a market size or a claim of exclusivity.",
         BURGUNDY, BURGUNDY_LIGHT),
    )
    for i, (tag, head, body, accent, fill) in enumerate(cards):
        x = MARGIN_X + i * (cw + GAP)
        box(s, x, sy, cw, status_h, fill=fill, line=accent, name=f"Status card {i + 1}")
        page.text(
            x + 0.15, sy + 0.05, cw - 0.3, status_h - 0.1,
            [Para(tag, 10.5, accent, bold=True, after=1), Para(head, 13, INK, bold=True, after=1),
             Para(body, 11, INK, after=0)],
            pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name=f"Status text {i + 1}",
        )
    notes.append("Status cards: verified evidence, unverified prices, assumption")
    page.finish(notes)


# ----------------------------------------------------------------------------- slide 5
def parse_weeks(bullets: list[str]) -> list[tuple[str, str]]:
    weeks = []
    for b in bullets:
        m = _WEEK.match(b)
        if m:
            weeks.append((f"Week {int(m.group(1))}", m.group(2).strip()))
    if weeks:
        return weeks
    return [(f"Step {i}", b) for i, b in enumerate(bullets, 1)]


def _slide_gtm(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    src, st = ctx.source, ctx.source.strategy
    top, height = page.top, page.height
    wa, wb = 3.9, 4.3
    wc = CONTENT_W - wa - wb - 2 * GAP
    xa, xb, xc = MARGIN_X, MARGIN_X + wa + GAP, MARGIN_X + wa + wb + 2 * GAP
    notes: list[str] = []

    # A: segment and positioning
    y = panel(s, xa, top, wa, height, "Target segment & positioning", accent=BURGUNDY)
    paras = [Para(src.input.target_customer, 18, INK, bold=True, font=HEAD_FONT, after=0)]
    h = needed_height_in(paras, wa - 0.4)
    page.text(xa + 0.2, y, wa - 0.4, h, paras, pad=0.02, name="Target segment")
    y += h + 0.02
    page.text(xa + 0.2, y, wa - 0.4, 0.3, Para(f"in {src.input.city}", 14, TEAL, bold=True,
                                                after=0), pad=0.02, name="Segment city")
    y += 0.42
    chip(s, xa + 0.2, y, "RECOMMENDATION", BURGUNDY_LIGHT, BURGUNDY, size=11, h=0.34,
         name="Positioning recommendation tag", line=BURGUNDY)
    y += 0.42
    page.text(xa + 0.2, y, wa - 0.4, top + height - y - 0.12, _bullets(spec.bullets, 14),
              pad=0.02, name="Positioning recommendations")

    # B: channels observed
    y = panel(s, xb, top, wb, height, "Channels observed in the market", accent=BLUE)
    seen: dict[str, list[str]] = {}
    for c in ctx.comps:
        for ch in c.channels:
            seen.setdefault(ch, []).append(c.name)
    rows = list(seen.items())[:6]
    row_h = 0.62
    if not rows:
        page.text(xb + 0.2, y, wb - 0.4, 0.6, Para("No channels were recorded.", 12, MUTED,
                                                    after=0), pad=0.02, name="No channels")
        y += 0.7
    for ch, who in rows:
        box(s, xb + 0.2, y, wb - 0.4, row_h - 0.08, fill=BLUE_LIGHT, line=BLUE,
            name=f"Channel: {ch}")
        page.text(xb + 0.3, y + 0.02, wb - 0.6, row_h - 0.12,
                  [Para(_short(ch, 60), 13, INK, bold=True, after=0),
                   Para("Seen at " + ", ".join(who), 11, MUTED, after=0)],
                  pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name=f"Channel text: {ch}")
        y += row_h
    if rows:
        page.text(xb + 0.2, y + 0.04, wb - 0.4, 0.5,
                  Para("Observed among the researched competitors; not a verified channel plan.",
                       10.5, MUTED, after=0, italic=True), pad=0.02, name="Channel caveat")
        y += 0.6
    prereq = [_short(t, 200) for t in _sentences(_unlabel(st.recommended_offer))[1:3]]
    if prereq and top + height - y > 0.8:
        page.text(xb + 0.2, y, wb - 0.4, 0.26,
                  Para("LAUNCH PREREQUISITES", 10.5, MUTED, bold=True, after=0), pad=0.02,
                  name="Prerequisites heading")
        page.text(xb + 0.2, y + 0.28, wb - 0.4, top + height - y - 0.4, _bullets(prereq, 12.5),
                  pad=0.02, name="Prerequisites")

    # C: phases
    y = panel(s, xc, top, wc, height, "Launch phases (recommended actions)", accent=TEAL)
    weeks = parse_weeks(src_plan(page))
    n = max(1, len(weeks))
    each = min(1.3, (top + height - y - 0.1) / n)
    if not weeks:
        page.text(xc + 0.2, y, wc - 0.4, 0.6, Para("No launch plan was recorded.", 12, MUTED,
                                                    after=0), pad=0.02, name="No phases")
    for i, (label, body) in enumerate(weeks, 1):
        badge(s, xc + 0.2, y + 0.04, 0.4, str(i), TEAL, WHITE, size=12, name=f"Phase badge {i}")
        page.text(xc + 0.72, y, wc - 0.9, each - 0.06,
                  [Para(label.upper(), 10.5, TEAL, bold=True, after=1),
                   Para(_short(_sentences(body)[0] if _sentences(body) else body, 200), 13,
                        INK, after=0)],
                  pad=0.02, name=f"Phase {i}")
        if i < len(weeks):
            arrow(s, xc + 0.4, y + 0.46, xc + 0.4, y + each + 0.02, TEAL, width_pt=1.5,
                  head=False, name=f"Phase link {i}")
        y += each
    notes.append(f"Phases shown: {len(weeks)}")
    page.finish(notes)


def src_plan(page: Page) -> list[str]:
    """Launch-plan bullets: the sixth slide's validated text (the saved 30-day plan)."""
    return page.ctx.deck.slides[5].bullets


# ----------------------------------------------------------------------------- slide 6
def _price_parts(raw: str) -> tuple[str, str, str, str]:
    """(headline amount, plan description, derived calculation, remaining note)."""
    match = _AMOUNT.search(raw or "")
    if not match:
        return "", "", "", (raw or "").strip()
    headline = f"{_currency(match.group(1))}{match.group(2)}"
    rest = raw[match.end() :].strip()
    derived = ""
    paren = re.search(r"\(([^)]*(?:about|approx|~)[^)]*)\)", rest, re.I)
    if paren:
        derived = paren.group(1).strip()
        rest = (rest[: paren.start()] + rest[paren.end() :]).strip()
    note = ""
    if ";" in rest:
        rest, note = (p.strip() for p in rest.split(";", 1))
    plan = re.sub(r"^(for|per)\s+(an?\s+)?", "", rest, flags=re.I).strip(" .,")
    return headline, plan[:1].upper() + plan[1:], derived, note


def _slide_financials(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    src, st = ctx.source, ctx.source.strategy
    top, height = page.top, page.height
    notes: list[str] = []
    top_h = height * 0.6
    wa, wb = 3.6, 5.2
    wc = CONTENT_W - wa - wb - 2 * GAP
    xa, xb, xc = MARGIN_X, MARGIN_X + wa + GAP, MARGIN_X + wa + wb + 2 * GAP

    # price
    y = panel(s, xa, top, wa, top_h, "Recommended test price", accent=BURGUNDY)
    head, plan, derived, note = _price_parts(st.recommended_price)
    if head:
        page.text(xa + 0.2, y, wa - 0.4, 0.7,
                  Para(head, 38, BURGUNDY, bold=True, font=HEAD_FONT, after=0), pad=0.02,
                  anchor=MSO_ANCHOR.MIDDLE, name="Price value")
        y += 0.74
        lines = [Para(plan, 13.5, INK, bold=True, after=3)] if plan else []
        if derived:
            lines.append(Para(derived[:1].upper() + derived[1:], 12.5, MUTED, after=3))
        if note:
            lines.append(Para(note[:1].upper() + note[1:], 12, MUTED, after=0))
    else:
        lines = [Para(st.recommended_price or "No price recommendation was recorded.", 12, INK,
                      after=0)]
    warn = [Para("RECOMMENDATION — NOT A VERIFIED MARKET PRICE", 10.5, GOLD, bold=True, after=0)]
    warn_h = needed_height_in(warn, wa - 0.4, pad=0.1) + 0.04
    wy = top + top_h - warn_h - 0.12
    if lines:
        page.text(xa + 0.2, y, wa - 0.4, max(0.3, wy - y - 0.06), lines, pad=0.02,
                  name="Price detail")
    page.text(xa + 0.2, wy, wa - 0.4, warn_h, warn, fill=GOLD_LIGHT, line=GOLD, pad=0.1,
              anchor=MSO_ANCHOR.MIDDLE, name="Price warning")

    # assumptions and unknowns
    y = panel(s, xb, top, wb, top_h, "Assumptions & unknowns", accent=GOLD)
    items = []
    for c in ctx.comps:
        if c.price.status != "verified":
            why = _short(_plain(c.unknowns[0]), 70) if c.unknowns else "no evidence-backed price"
            items.append(f"{c.name}: price not verified ({why})")
    assume = [_short(t, 200) for t in _sentences(_plain(st.rationale))[:3]]
    paras = [Para("UNVERIFIED", 10.5, GOLD, bold=True, after=2)]
    if len(items) > 4:
        items = [*items[:4], f"+{len(items) - 4} more competitor price(s) not verified"]
    paras += _bullets(items or ["All competitor prices were verified."], 12)
    paras += [Para("ASSUMPTIONS (FROM THE REPORT'S RATIONALE)", 10.5, GOLD, bold=True, after=2)]
    paras += _bullets(assume or ["No rationale was recorded."], 12)
    page.text(xb + 0.2, y, wb - 0.35, top + top_h - y - 0.1, paras, pad=0.02,
              name="Assumptions and unknowns")

    # next steps
    y = panel(s, xc, top, wc, top_h, "Next steps & priorities", accent=TEAL)
    weeks = parse_weeks(spec.bullets)
    steps = []
    if weeks:
        steps.append(f"Start: {_short(weeks[0][1], 220)}")
    if src.partial:
        steps += [f"Close gap: {_short(r, 180)}" for r in src.acceptance_reasons[:2]]
    else:
        steps.append("Report passed acceptance: proceed with the roadmap below.")
    page.text(xc + 0.2, y, wc - 0.35, top + top_h - y - 0.1, _bullets(steps, 12.5), pad=0.02,
              name="Next steps")

    # roadmap
    ry = top + top_h + GAP
    page.text(MARGIN_X, ry, CONTENT_W, 0.3,
              Para("30-DAY ROADMAP · RECOMMENDED ACTIONS, NOT COMPLETED OR VERIFIED FACTS", 11,
                   BURGUNDY, bold=True, after=0), pad=0.02, name="Roadmap heading")
    cy = ry + 0.34
    ch = top + height - cy
    n = max(1, len(weeks))
    cw = (CONTENT_W - GAP * (n - 1)) / n
    if not weeks:
        page.text(MARGIN_X, cy, CONTENT_W, 0.5, Para("No launch plan steps were recorded.", 12,
                                                    MUTED, after=0), pad=0.02, name="No plan")
    for i, (label, body) in enumerate(weeks):
        x = MARGIN_X + i * (cw + GAP)
        box(s, x, cy, cw, ch, fill=PAPER, line=BORDER, name=f"Milestone {i + 1}")
        box(s, x, cy, cw, 0.07, fill=TEAL if i % 2 == 0 else BLUE, round_=False, name="Accent")
        chip(s, x + 0.15, cy + 0.16, label.upper(), TEAL_LIGHT, TEAL, size=10.5, h=0.32,
             name=f"Milestone tag {i + 1}", line=TEAL)
        page.text(x + 0.15, cy + 0.56, cw - 0.3, ch - 0.64, Para(body, 12, INK, after=0),
                  pad=0.02, name=f"Milestone text {i + 1}")
        if i < n - 1:
            arrow(s, x + cw, cy + ch / 2, x + cw + GAP, cy + ch / 2, TEAL, width_pt=2,
                  name=f"Timeline link {i + 1}")
    notes.append(f"Roadmap weeks: {len(weeks)}")
    page.finish(notes)


# ----------------------------------------------------------------------------- entry points
_LAYOUTS = (
    _slide_problem,
    _slide_market,
    _slide_customers,
    _slide_solution,
    _slide_gtm,
    _slide_financials,
)


def build_pptx(deck: DeckSpec, source: DeckSource, path: Path, generated_on: date) -> Path:
    """Write the deck: exactly six slides, native editable shapes, LS logo on every slide."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(int(Inches(SLIDE_W))), Emu(int(Inches(SLIDE_H)))
    ctx = Ctx(deck, source, generated_on)
    for index, (layout, slide_spec) in enumerate(zip(_LAYOUTS, deck.slides, strict=True), 1):
        layout(Page(prs, ctx, index, slide_spec))
    prs.core_properties.title = f"LaunchScout pitch deck: {source.input.idea}"
    prs.core_properties.author = "LaunchScout"
    path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(path))
    return path


_A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _frame_needed_pt(shape) -> float:
    frame = shape.text_frame
    width_pt = shape.width / 12700 - (frame.margin_left + frame.margin_right) / 12700
    total = 0.0
    for para in frame.paragraphs:
        size = max((r.font.size.pt for r in para.runs if r.font.size), default=14.0)
        serif = any(r.font.name == HEAD_FONT for r in para.runs)
        eff = size * (SERIF_EM_FACTOR if serif else 1.0)
        ppr = para._p.pPr
        bulleted = ppr is not None and ppr.find(f"{_A_NS}buChar") is not None
        content = "".join(r.text for r in para.runs)
        lines = estimate_lines(content, width_pt - (16 if bulleted else 0), eff)
        after = para.space_after.pt if para.space_after is not None else 0
        total += lines * size * LINE_SPACING + after
    return total + (frame.margin_top + frame.margin_bottom) / 12700


def check_text_bounds(path: Path) -> list[str]:
    """Programmatic layout check (an estimate, not a render).

    Flags: text likely to overflow its shape (including multiline banners), content below the
    footer rule, shapes outside the slide, overlapping text shapes and a missing logo.
    """
    prs = Presentation(str(path))
    problems: list[str] = []
    footer_top = int(Inches(FOOTER_TOP))
    for number, slide in enumerate(prs.slides, 1):
        text_shapes = []
        if "LS logo" not in {s.name for s in slide.shapes}:
            problems.append(f"slide {number}: LS logo is missing")
        for shape in slide.shapes:
            outside = (
                shape.left < 0
                or shape.top < 0
                or shape.left + shape.width > prs.slide_width + 10
                or shape.top + shape.height > prs.slide_height + 10
            )
            if outside:
                problems.append(f"slide {number}: '{shape.name}' extends outside the slide")
            if shape.name not in _FOOTER_NAMES and shape.top + shape.height > footer_top + 10:
                problems.append(f"slide {number}: '{shape.name}' runs into the footer")
            if not shape.has_text_frame or not shape.text_frame.text.strip():
                continue
            if _frame_needed_pt(shape) * 12700 > shape.height * 1.02:
                what = (
                    "label text may wrap outside its banner"
                    if shape.name == "Labels"
                    else f"text may overflow '{shape.name}'"
                )
                problems.append(f"slide {number}: {what}")
            text_shapes.append(shape)
        for i, a in enumerate(text_shapes):
            for b in text_shapes[i + 1 :]:
                dx = min(a.left + a.width, b.left + b.width) - max(a.left, b.left)
                dy = min(a.top + a.height, b.top + b.height) - max(a.top, b.top)
                if dx > 0 and dy > 0:
                    smaller = min(a.width * a.height, b.width * b.height)
                    if dx * dy > 0.04 * smaller:
                        problems.append(f"slide {number}: '{a.name}' overlaps '{b.name}'")
    return problems


def layout_utilization(path: Path) -> list[float]:
    """Share of the content band (below the header, above the footer, between margins)
    covered by shapes, per slide. A coarse grid estimate of space use."""
    prs = Presentation(str(path))
    out: list[float] = []
    band_top, band_bottom = _HEADER_BOTTOM + 0.1, FOOTER_TOP
    cols, rows = 96, 48
    for slide in prs.slides:
        grid = [[False] * cols for _ in range(rows)]
        for shape in slide.shapes:
            if shape.name in _FOOTER_NAMES:
                continue
            x0, x1 = shape.left / 914400, (shape.left + shape.width) / 914400
            y0, y1 = shape.top / 914400, (shape.top + shape.height) / 914400
            for r in range(rows):
                cy = band_top + (r + 0.5) * (band_bottom - band_top) / rows
                if not y0 <= cy <= y1:
                    continue
                for c in range(cols):
                    if x0 <= (c + 0.5) * SLIDE_W / cols <= x1:
                        grid[r][c] = True
        cells = [
            grid[r][c]
            for r in range(rows)
            for c in range(cols)
            if MARGIN_X <= (c + 0.5) * SLIDE_W / cols <= SLIDE_W - MARGIN_X
        ]
        out.append(sum(cells) / len(cells))
    return out
