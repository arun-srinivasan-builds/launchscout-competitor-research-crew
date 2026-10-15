"""Render a `DeckSpec` as a premium, fully editable six-slide investor presentation (V4).

Slides are composed from native shapes, pictograms built from autoshapes, native charts, text
boxes and connectors (no flattened images); the only picture is the approved LS logo. Every
number and sentence comes from the saved research (`DeckSource`) and the validated `DeckSpec`;
nothing is hardcoded to one business idea, and missing evidence is shown as missing. Verified
findings, inferences, recommendations and unknowns keep distinct labels. On-slide text is a
complete clause or sentence (never cut mid-thought); the full wording is kept in the notes.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

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
    _shorten,
    arrow,
    box,
    chip,
    chip_width,
    estimate_lines,
    icon,
    needed_height_in,
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
SLIDE_SUBTITLES = (
    "Who the research is for, what the market shows and where an opportunity may lie",
    "Researched competitors, their offers and channels, and the evidence behind them",
    "What retrieved customer feedback says, and what it cannot tell us",
    "From observed evidence to a recommended, differentiated offer",
    "Recommended positioning and a phased launch, apart from observed channels",
    "The recommended test price, what is unknown and the decision checkpoints",
)
THEMES = (  # a generic review-theme lexicon: counts are keyword matches, never sentiment scores
    ("Taste & flavour", ("flavor", "flavour", "taste", "tasty", "delicious", "sweet", "tart")),
    ("Freshness & natural ingredients", ("fresh", "natural", "organic", "ingredient", "pure",
                                         "preservative")),
    ("Energy & wellbeing", ("energy", "energetic", "healthy", "nutrient", "wellness", "boost")),
    ("Convenience & delivery", ("deliver", "convenient", "easy", "doorstep", "subscription")),
    ("Quality & trust", ("quality", "trust", "reliable", "consistent", "peace of mind")),
    ("Value & price", ("price", "value", "affordable", "worth", "cheap")),
)
_AMOUNT = re.compile(r"(₹|Rs\.?|INR|\$|USD|€|EUR)\s?(\d[\d,]*(?:\.\d+)?)", re.I)
_WEEK = re.compile(r"^\s*week\s*(\d+)\s*[:\-–—]\s*(.+)$", re.I | re.S)
_URL = re.compile(r"https?://\S+")
_FOOTER_NAMES = ("Footer", "Footer rule", "Slide number")
_HEADER_BOTTOM = 0.98


# ----------------------------------------------------------------------------- text helpers
def _host(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0]


def _currency(symbol: str) -> str:
    return "₹" if symbol.upper() in ("INR", "RS", "RS.") else symbol


def _plain(value: str) -> str:
    """Text without bare URLs (they stay in the source list and the notes)."""
    no_urls = _URL.sub("", value or "")
    no_urls = re.sub(r"\s*;\s*;", ";", no_urls)
    return " ".join(no_urls.replace(" ;", ";").split()).strip(" ;,")


def _sentences(value: str) -> list[str]:
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", _plain(value)) if s.strip()]
    return parts


def _unlabel(value: str) -> str:
    cleaned = re.sub(r"^\s*recommendation\s*:\s*", "", value or "", flags=re.I).strip()
    cleaned = cleaned.strip("\"'“”‘’ ")
    return cleaned[:1].upper() + cleaned[1:]


def _clause(value: str, limit: int) -> str:
    """The first complete sentence/clause of `value` within `limit` characters."""
    text = " ".join(_plain(value).split())
    if not text:
        return ""
    first = (_sentences(text)[0] if _sentences(text) else text).rstrip(".")
    if len(first) <= limit:
        return first
    head = first.split("; ")[0].strip()
    if 25 <= len(head) <= limit:
        return head
    return _shorten(first, limit).rstrip(".")


def _channel(label: str) -> str:
    """A channel label without its parenthetical qualifier."""
    return re.sub(r"\s*\(.*?\)", "", label or "").strip() or (label or "")


def _clauses(value: str) -> list[str]:
    """Semicolon-separated clauses of a plan or finding."""
    return [c.strip(" .") for c in re.split(r";\s+", _plain(value)) if c.strip(" .")]


def _initials(name: str) -> str:
    words = [w for w in re.split(r"\W+", name) if w]
    return "".join(w[0].upper() for w in words[:2]) or "?"


def _short_run(run_id: str) -> str:
    parts = run_id.split("-")
    if len(parts) >= 3 and parts[0].isdigit():
        return f"{parts[0]}-{parts[1]}-{parts[-1]}"
    return run_id[:24]


def _bullets(items: list[str], size: float = 12.5, color=INK, after: float = 5) -> list[Para]:
    return [Para(i, size, color, bullet=True, after=after) for i in items]


def parse_weeks(bullets: list[str]) -> list[tuple[str, str]]:
    weeks = []
    for b in bullets:
        m = _WEEK.match(b)
        if m:
            weeks.append((f"Week {int(m.group(1))}", m.group(2).strip()))
    if weeks:
        return weeks
    return [(f"Step {i}", b) for i, b in enumerate(bullets, 1)]


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


def _split_quote(text: str) -> tuple[str, str]:
    """(quotation, attribution) from a stored finding such as “…” — attributed on X to Y."""
    m = re.search(r"[“\"](.+?)[”\"]", text, re.S)
    if m:
        quote = m.group(1).strip()
        rest = (text[: m.start()] + text[m.end() :]).strip(" —-–")
        return quote, rest
    return text.strip(), ""


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

    def theme_counts(self) -> list[tuple[str, int]]:
        texts = [f.text.lower() for f in self.source.reviews.findings]
        counts = []
        for name, words in THEMES:
            n = sum(1 for t in texts if any(w in t for w in words))
            if n:
                counts.append((name, n))
        return sorted(counts, key=lambda kv: (-kv[1], kv[0]))


# ----------------------------------------------------------------------------- page chrome
class Page:
    """One slide: compact branded header, status banner, sources strip and footer."""

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
        box(s, MARGIN_X, 0.2, 3.0, 0.7, fill=INK, name="Brand block")
        box(s, MARGIN_X + 0.1, 0.28, 0.54, 0.54, fill=WHITE, name="LS logo tile")
        pic_h = 0.43
        pic_w = pic_h * LOGO_ASPECT
        pic = s.shapes.add_picture(
            str(LOGO_FILE),
            Inches(MARGIN_X + 0.1 + (0.54 - pic_w) / 2),
            Inches(0.335),
            height=Inches(pic_h),
        )
        pic.name = "LS logo"
        pic._element.nvPicPr.cNvPr.set("descr", "LaunchScout LS logo")
        text_box(s, MARGIN_X + 0.78, 0.2, 2.15, 0.34,
                 Para("LaunchScout", 17, WHITE, bold=True, font=HEAD_FONT, after=0), pad=0.02,
                 name="Brand name")
        text_box(s, MARGIN_X + 0.78, 0.56, 2.15, 0.27,
                 Para("Competitor Research Crew", 10.5, TEAL_ON_INK, bold=True, after=0),
                 pad=0.02, name="Brand tagline")
        label = ctx.status_label
        width = chip_width(label, 11)
        status_fill = GOLD_LIGHT if ctx.source.partial else TEAL_LIGHT
        status_color = GOLD if ctx.source.partial else TEAL
        chip(s, SLIDE_W - MARGIN_X - width, 0.37, label, status_fill, status_color, size=11,
             h=0.34, name="Evidence status", line=status_color)
        title_x = MARGIN_X + 3.0 + 0.3
        text_box(s, title_x, 0.17, 0.85, 0.46,
                 Para(f"{self.index:02d}.", 24, GOLD, bold=True, font=HEAD_FONT, after=0),
                 pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name="Slide index")
        title_w = SLIDE_W - MARGIN_X - width - 0.25 - (title_x + 0.85)
        text_box(s, title_x + 0.85, 0.17, title_w, 0.46,
                 Para(SLIDE_NAMES[self.index - 1], 24, BURGUNDY, bold=True, font=HEAD_FONT,
                      after=0), pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name="Title")
        text_box(s, title_x + 0.85, 0.63, title_w, 0.28,
                 Para(SLIDE_SUBTITLES[self.index - 1], 11.5, MUTED, after=0),
                 pad=0.02, name="Subtitle")

    def _banner(self) -> float:
        top = _HEADER_BOTTOM + 0.1
        if self.spec.labels:
            paras = [Para("   ·   ".join(self.spec.labels), 11, BURGUNDY, bold=True, after=0)]
            h = needed_height_in(paras, CONTENT_W, pad=0.12) + 0.04
            text_box(self.slide, MARGIN_X, top, CONTENT_W, h, paras, fill=BURGUNDY_LIGHT,
                     line=BURGUNDY, pad=0.12, anchor=MSO_ANCHOR.MIDDLE, name="Labels")
            top += h + 0.12
        return top

    def _sources(self) -> float:
        refs: list[str] = []
        for ref in self.spec.source_refs:
            label = _host(ref) if ref.startswith("http") else ref
            if label and label not in refs:
                refs.append(label)
        shown = " · ".join(refs[:6]) + (f" · +{len(refs) - 6} more" if len(refs) > 6 else "")
        line = f"Sources: {shown}" if refs else "Sources: none cited for this slide"
        y = CONTENT_BOTTOM - 0.26
        text_box(self.slide, MARGIN_X, y, CONTENT_W, 0.26,
                 Para(_shorten(line, 200), 10.5, MUTED, after=0), pad=0.02,
                 anchor=MSO_ANCHOR.MIDDLE, name="Sources")
        return y - 0.06

    def finish(self, extra: list[str]) -> None:
        s, ctx = self.slide, self.ctx
        arrow(s, MARGIN_X, FOOTER_TOP, SLIDE_W - MARGIN_X, FOOTER_TOP, BORDER, width_pt=1.0,
              head=False, name="Footer rule")
        footer = (
            f"LaunchScout | {SLIDE_NAMES[self.index - 1]} | "
            f"{ctx.source.input.idea}, {ctx.source.input.city} | "
            f"{'Partial evidence' if ctx.source.partial else 'Validated report'} | "
            f"run {_short_run(ctx.source.run_id)}"
        )
        text_box(s, MARGIN_X, FOOTER_TOP + 0.04, CONTENT_W - 1.2, 0.28,
                 Para(footer, 10, MUTED, after=0), pad=0.02, name="Footer")
        text_box(s, SLIDE_W - MARGIN_X - 1.1, FOOTER_TOP + 0.03, 1.1, 0.3,
                 Para(f"{self.index:02d} / 06", 11, BURGUNDY, bold=True, align=PP_ALIGN.RIGHT,
                      after=0), pad=0.02, name="Slide number")
        tail = [f"Validated deck title: {self.spec.title}", f"Run: {ctx.source.run_id}"]
        if self.full:
            tail += ["Full text of items shortened on the slide:"] + [f"  {t}" for t in self.full]
        _notes(s, self.spec, extra + tail)


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


# ----------------------------------------------------------------------------- shared visuals
def _card(page: Page, x, y, w, h, fill=PAPER, line=BORDER, name="Card"):
    return box(page.slide, x, y, w, h, fill=fill, line=line, name=name)


def _heading(page: Page, x, y, w, label: str, color=BURGUNDY) -> None:
    page.text(x, y, w, 0.3, Para(label.upper(), 11, color, bold=True, after=0), pad=0.02,
              name=f"Heading: {label}")


def _pills(page: Page, x, y, w, labels: list[str], fill, color, *, size=10.5, h=0.3, name="Pill"):
    """Rows of small pills; returns the y after the last row."""
    cx, cy = x, y
    for label in labels:
        pw = chip_width(label, size)
        if cx + pw > x + w and cx > x:
            cx, cy = x, cy + h + 0.08
        chip(page.slide, cx, cy, label, fill, color, size=size, h=h, name=f"{name}: {label}",
             line=color)
        cx += pw + 0.1
    return cy + h


def _doughnut(page: Page, x, y, d, have: int, total: int, color, name: str) -> None:
    data = CategoryChartData()
    data.categories = ["Met", "Missing"]
    gap = max(total - have, 0)
    data.add_series("Gate", (have, gap if (have or gap) else 1))
    frame = page.slide.shapes.add_chart(
        XL_CHART_TYPE.DOUGHNUT, Inches(x), Inches(y), Inches(d), Inches(d), data
    )
    frame.name = name
    chart = frame.chart
    chart.has_legend = False
    chart.has_title = False
    plot = chart.plots[0]
    plot.has_data_labels = False
    pts = plot.series[0].points
    pts[0].format.fill.solid()
    pts[0].format.fill.fore_color.rgb = color
    pts[1].format.fill.solid()
    pts[1].format.fill.fore_color.rgb = BORDER
    for pt in (pts[0], pts[1]):
        pt.format.line.color.rgb = PAPER
    hole = plot._element.find(
        "{http://schemas.openxmlformats.org/drawingml/2006/chart}holeSize"
    )
    if hole is not None:
        hole.set("val", "68")


def _bar_chart(page: Page, x, y, w, h, rows: list[tuple[str, int]], name: str) -> None:
    data = CategoryChartData()
    data.categories = [r[0] for r in rows]
    data.add_series("Testimonials mentioning the theme", [r[1] for r in rows])
    frame = page.slide.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), data
    )
    frame.name = name
    chart = frame.chart
    chart.has_legend = False
    chart.has_title = False
    chart.font.size = Pt(12)
    chart.font.name = "Calibri"
    chart.font.color.rgb = INK
    cat = chart.category_axis
    cat.reverse_order = True
    cat.format.line.color.rgb = BORDER
    cat.tick_labels.font.size = Pt(12)
    val = chart.value_axis
    val.visible = False
    val.has_major_gridlines = False
    val.minimum_scale = 0
    val.maximum_scale = max(r[1] for r in rows) + 1
    plot = chart.plots[0]
    plot.gap_width = 55
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.position = XL_LABEL_POSITION.OUTSIDE_END
    labels.font.size = Pt(12)
    labels.font.bold = True
    labels.font.color.rgb = INK
    series = plot.series[0]
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = TEAL


# ----------------------------------------------------------------------------- slide 1
def _slide_problem(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    src, inp = ctx.source, ctx.source.input
    st = src.strategy
    top, height = page.top, page.height
    wa, wb = 4.6, 4.3
    wc = CONTENT_W - wa - wb - 2 * GAP
    xa, xb, xc = MARGIN_X, MARGIN_X + wa + GAP, MARGIN_X + wa + wb + 2 * GAP
    notes: list[str] = []

    # A: the opportunity statement
    _card(page, xa, top, wa, height, name="Opportunity card")
    box(s, xa + 0.12, top + 0.25, 0.07, height - 0.5, fill=BURGUNDY, round_=False, name="Accent")
    _heading(page, xa + 0.35, top + 0.16, wa - 0.6, "The opportunity")
    paras = [
        Para(inp.idea, 30, INK, bold=True, font=HEAD_FONT, after=8),
        Para(f"for {inp.target_customer} in {inp.city}", 17, TEAL, bold=True, after=0),
    ]
    h = needed_height_in(paras, wa - 0.7)
    page.text(xa + 0.35, top + 0.52, wa - 0.7, h, paras, pad=0.02, name="Business idea")
    y = top + 0.52 + h + 0.2
    box(s, xa + 0.35, y, wa - 0.7, 0.015, fill=BORDER, round_=False, name="Divider")
    _heading(page, xa + 0.35, y + 0.12, wa - 0.7, "Research summary", MUTED)
    page.text(xa + 0.35, y + 0.46, wa - 0.7, top + height - y - 0.6,
              _bullets(spec.bullets, 13.5), pad=0.02, name="Research summary")

    # B: customer -> market -> gap -> response journey
    channels = sorted({ch for c in ctx.comps for ch in c.channels})
    market = (
        f"{len(ctx.comps)} competitors researched, {ctx.n_evidence} with public evidence URLs"
        + (f"; channels seen: {', '.join(channels[:3])}" if channels else "")
    )
    gap_source = ctx.deck.slides[3].bullets[0] if ctx.deck.slides[3].bullets else st.market_gap
    gap = _clause(gap_source, 170) or "No market-gap statement was recorded."
    response = _clause(_unlabel(st.positioning_line) or st.recommended_offer, 160) or (
        "No positioning statement was recorded."
    )
    rows = (
        ("TARGET CUSTOMER", f"{inp.target_customer} in {inp.city}", "person", TEAL),
        ("OBSERVED IN THE MARKET · VERIFIED PAGES", market, "chart", BLUE),
        ("RESEARCH-VISIBLE GAP · INFERENCE", gap, "target", BURGUNDY),
        ("RECOMMENDED RESPONSE · RECOMMENDATION", response, "star", GOLD),
    )
    row_h = height / len(rows)
    d = 0.7
    box(s, xb + d / 2 - 0.02, top + row_h / 2, 0.04, row_h * (len(rows) - 1), fill=BORDER,
        round_=False, name="Journey line")
    for i, (label, body, glyph, color) in enumerate(rows, 1):
        ry = top + (i - 1) * row_h
        icon(s, xb, ry + (row_h - d) / 2, d, glyph, color, name=f"Journey {i}")
        page.text(xb + d + 0.18, ry + 0.08, wb - d - 0.2, row_h - 0.16,
                  [Para(label, 10.5, color, bold=True, after=2), Para(body, 13, INK, after=0)],
                  pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name=f"Journey text {i}")
    notes.append("Journey: target customer, observed market, inferred gap, recommended response")

    # C: research scope and status
    _card(page, xc, top, wc, height, name="Scope card")
    _heading(page, xc + 0.2, top + 0.16, wc - 0.4, "Research scope & status", TEAL)
    dd = 1.18
    gx1 = xc + wc / 2 - dd - 0.1
    gx2 = xc + wc / 2 + 0.1
    gy = top + 0.55
    for gx, have, label, color, key in (
        (gx1, ctx.n_evidence, "Competitors with evidence", TEAL, "competitors"),
        (gx2, ctx.n_verified, "Verified competitor prices", GOLD, "prices"),
    ):
        _doughnut(page, gx, gy, dd, have, GATE_MIN, color, f"Gauge chart: {key}")
        page.text(gx + 0.2, gy + dd / 2 - 0.22, dd - 0.4, 0.44,
                  Para(f"{have}/{GATE_MIN}", 17, INK, bold=True, font=HEAD_FONT,
                       align=PP_ALIGN.CENTER, after=0), pad=0.0, anchor=MSO_ANCHOR.MIDDLE,
                  name=f"Gauge value: {key}")
        page.text(gx - 0.1, gy + dd + 0.04, dd + 0.2, 0.5,
                  Para(label, 10.5, MUTED, bold=True, align=PP_ALIGN.CENTER, after=0), pad=0.02,
                  name=f"Gauge label: {key}")
    y = gy + dd + 0.66
    mode = getattr(inp.mode, "value", inp.mode)
    facts = (
        ("Sources reviewed", str(len(src.evidence_urls)) if src.evidence_urls else "none"),
        ("Report status", "Partial acceptance" if src.partial else "Validated"),
    )
    notes.append(f"Research mode: {str(mode).title()}")
    for label, value in facts:
        page.text(xc + 0.2, y, wc - 0.4, 0.46,
                  [Para(label.upper(), 10, MUTED, bold=True, after=0),
                   Para(value, 13, INK, bold=True, after=0)], pad=0.02, name=f"Fact: {label}")
        y += 0.5
    if src.partial and src.acceptance_reasons:
        reasons = [_clause(r, 110) for r in src.acceptance_reasons[:2]]
        page.text(xc + 0.2, y + 0.04, wc - 0.4, top + height - y - 0.12,
                  [Para("WHY PARTIAL", 10, MUTED, bold=True, after=2)]
                  + _bullets(reasons, 11, INK, 3), pad=0.02, name="Acceptance gaps")
    page.finish(notes)


# ----------------------------------------------------------------------------- slide 2
def _slide_market(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    top, height = page.top, page.height
    lw = 7.5
    rw = CONTENT_W - lw - GAP
    xr = MARGIN_X + lw + GAP
    comps = ctx.comps
    notes: list[str] = []

    tints = (BLUE_LIGHT, GOLD_LIGHT, TEAL_LIGHT)
    n = max(1, len(comps))
    gap = GAP if n <= 3 else 0.08
    card_h = min(2.5, (height - gap * (n - 1)) / n)
    rows_mode = card_h < 1.25  # many competitors: one compact row each
    compact = card_h < 1.7
    if not comps:
        _card(page, MARGIN_X, top, lw, 1.2, name="No competitors")
        page.text(MARGIN_X + 0.25, top + 0.25, lw - 0.5, 0.7,
                  Para("No competitor met the evidence threshold in the saved research.", 14,
                       MUTED, after=0), pad=0.02, name="No competitors text")
    for i, comp in enumerate(comps):
        y = top + i * (card_h + gap)
        box(s, MARGIN_X, y, lw, card_h, fill=tints[i % 3], name=f"Competitor: {comp.name}")
        verified = comp.price.status == "verified" and comp.price.amount is not None
        label = (f"{_currency(comp.price.currency or '')}{comp.price.amount:g}" if verified
                 else "PRICE UNKNOWN")
        cw_ = chip_width(label, 11)
        if rows_mode:
            md = min(0.46, card_h - 0.12)
            page.text(MARGIN_X + 0.15, y + (card_h - md) / 2, md, md,
                      Para(_initials(comp.name), 11, WHITE, bold=True, font=HEAD_FONT,
                           align=PP_ALIGN.CENTER, after=0),
                      fill=INK if i % 2 == 0 else BURGUNDY, shape=MSO_SHAPE.OVAL, pad=0.0,
                      anchor=MSO_ANCHOR.MIDDLE, wrap=False, name=f"Monogram: {comp.name}")
            chip(s, MARGIN_X + lw - 0.15 - cw_, y + (card_h - 0.3) / 2, label, WHITE,
                 TEAL if verified else GOLD, size=10, h=0.3, name=f"Price: {comp.name}",
                 line=TEAL if verified else GOLD)
            tx = MARGIN_X + 0.15 + md + 0.15
            page.text(tx, y + 0.04, lw - (tx - MARGIN_X) - cw_ - 0.35, card_h - 0.08,
                      [Para(comp.name, 12, INK, bold=True, after=0),
                       Para(_clause(comp.offer, 90) or "Offer not recorded.", 10.5, INK,
                            after=0)], pad=0.02, anchor=MSO_ANCHOR.MIDDLE,
                      name=f"Name: {comp.name}")
            continue
        md = 0.8 if not compact else 0.56
        page.text(MARGIN_X + 0.2, y + 0.16, md, md,
                  Para(_initials(comp.name), 20 if not compact else 14, WHITE, bold=True,
                       font=HEAD_FONT, align=PP_ALIGN.CENTER, after=0),
                  fill=INK if i % 2 == 0 else BURGUNDY, shape=MSO_SHAPE.OVAL, pad=0.0,
                  anchor=MSO_ANCHOR.MIDDLE, wrap=False, name=f"Monogram: {comp.name}")
        chip(s, MARGIN_X + lw - 0.2 - cw_, y + 0.2, label, WHITE, TEAL if verified else GOLD,
             size=11, h=0.34, name=f"Price: {comp.name}", line=TEAL if verified else GOLD)
        text_x = MARGIN_X + 0.2 + md + 0.2
        text_w = lw - (text_x - MARGIN_X) - cw_ - 0.45
        head = [Para(comp.name, 17 if not compact else 14, INK, bold=True, font=HEAD_FONT,
                     after=0)]
        if not compact:
            head.append(Para(_host(comp.url), 11, MUTED, after=0))
        page.text(text_x, y + 0.14, text_w, 0.7 if not compact else 0.4, head, pad=0.02,
                  name=f"Name: {comp.name}")
        body_y = y + (1.0 if not compact else 0.74)
        offer = _clause(comp.offer, 170) or "Offer not recorded."
        page.text(MARGIN_X + 0.25, body_y, lw - 0.5, 0.62 if not compact else 0.42,
                  Para(offer, 13 if not compact else 11, INK, after=0), pad=0.02,
                  name=f"Offer: {comp.name}")
        pill_y = body_y + (0.7 if not compact else 0.46)
        channels = [_channel(c) for c in comp.channels[:3]] or ["Channels not recorded"]
        pill_end = _pills(page, MARGIN_X + 0.25, pill_y, lw - 2.4, channels, WHITE, TEAL,
                          size=10.5, name=f"Channel {comp.name}")
        urls = f"{len(comp.evidence_urls)} source URL(s)"
        page.text(MARGIN_X + lw - 2.2, pill_y - 0.02, 2.0, 0.3,
                  Para(urls, 11, MUTED, bold=True, align=PP_ALIGN.RIGHT, after=0), pad=0.02,
                  name=f"Sources count: {comp.name}")
        if comp.unknowns and not compact:
            page.text(MARGIN_X + 0.25, pill_end + 0.1, lw - 0.5, y + card_h - pill_end - 0.18,
                      Para("Unknown: " + _clause(comp.unknowns[0], 150), 11, MUTED, after=0),
                      pad=0.02, name=f"Unknown: {comp.name}")

    # right top: evidence coverage grid
    shown = comps[:4]
    attrs: list[tuple[str, list[bool]]] = []
    seen_channels: list[str] = []
    for ch in sorted({_channel(c) for comp in comps for c in comp.channels}):
        if ch not in seen_channels:
            seen_channels.append(ch)
    for ch in seen_channels[:4]:
        attrs.append((ch, [any(_channel(x) == ch for x in c.channels) for c in shown]))
    attrs.append(("Price verified", [c.price.status == "verified" for c in shown]))
    attrs.append(("Offer page cited", [bool(c.evidence_urls) for c in shown]))
    findings = ctx.source.reviews.findings
    attrs.append(("Testimonials retrieved",
                  [any(f.competitor.casefold() == c.name.casefold() for f in findings)
                   for c in shown]))
    row_h = 0.33
    gh = 0.7 + row_h * len(attrs) + 0.12
    _card(page, xr, top, rw, gh, name="Coverage grid card")
    _heading(page, xr + 0.2, top + 0.14, rw - 0.4, "Evidence footprint", TEAL)
    label_w = 2.05
    col_w = (rw - label_w - 0.3) / max(1, len(shown))
    for j, c in enumerate(shown):
        page.text(xr + 0.2 + label_w + j * col_w, top + 0.5, col_w, 0.26,
                  Para(c.name.split()[0], 10.5, MUTED, bold=True, align=PP_ALIGN.CENTER,
                       after=0), pad=0.0, name=f"Grid column: {c.name}")
    for r, (label, flags) in enumerate(attrs):
        ry = top + 0.78 + r * row_h
        page.text(xr + 0.2, ry, label_w, row_h - 0.04,
                  Para(label, 11.5, INK, after=0), pad=0.02, anchor=MSO_ANCHOR.MIDDLE,
                  name=f"Grid row: {label}")
        for j, ok in enumerate(flags):
            cx = xr + 0.2 + label_w + j * col_w + col_w / 2 - 0.1
            box(s, cx, ry + row_h / 2 - 0.12, 0.2, 0.2, fill=TEAL if ok else PAPER,
                line=TEAL if ok else BORDER, shape=MSO_SHAPE.OVAL, line_w=1.25,
                name=f"Grid {'present' if ok else 'absent'}: {label} / {shown[j].name}")

    # right bottom: key findings
    fy = top + gh + GAP
    _card(page, xr, fy, rw, top + height - fy, name="Findings card")
    _heading(page, xr + 0.2, fy + 0.14, rw - 0.4, "Key findings", BURGUNDY)
    items = [_clause(b, 100) for b in spec.bullets if "price unknown" not in b.lower()][:3]
    page.text(xr + 0.2, fy + 0.46, rw - 0.4, top + height - fy - 0.56,
              _bullets(items, 11.5, INK, 4), pad=0.02, name="Findings")
    notes.append("Evidence footprint: filled dot = present in the saved research")
    page.finish(notes)


# ----------------------------------------------------------------------------- slide 3
def _slide_customers(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    top, height = page.top, page.height
    findings = list(ctx.source.reviews.findings)
    praise = sum(1 for f in findings if f.kind == "praise")
    complaint = len(findings) - praise
    notes: list[str] = []
    wl, wm = 4.4, 4.6
    wr = CONTENT_W - wl - wm - 2 * GAP
    xl, xm, xr = MARGIN_X, MARGIN_X + wl + GAP, MARGIN_X + wl + wm + 2 * GAP

    # left: theme chart
    _card(page, xl, top, wl, height, name="Themes card")
    _heading(page, xl + 0.2, top + 0.16, wl - 0.4, "What the testimonials mention", TEAL)
    themes = ctx.theme_counts()
    if themes:
        _bar_chart(page, xl + 0.1, top + 0.5, wl - 0.2, height - 1.5, themes[:6],
                   "Chart: Testimonial themes")
    else:
        page.text(xl + 0.25, top + 0.6, wl - 0.5, 0.8,
                  Para("No recurring theme could be derived from the retrieved feedback.", 13,
                       MUTED, after=0), pad=0.02, name="No themes")
    page.text(xl + 0.2, top + height - 0.9, wl - 0.4, 0.78,
              Para(f"Keyword mentions across {len(findings)} retrieved testimonial(s). A "
                   "theme count is not a sentiment score.", 11, MUTED, after=0, italic=True),
              pad=0.02, name="Chart caveat")

    # middle: attributed highlights, one per competitor
    by_comp: dict[str, list] = {}
    for f in findings:
        by_comp.setdefault(f.competitor, []).append(f)
    picks = [group[0] for group in by_comp.values()][:3]
    k = max(1, len(picks))
    qh = (height - GAP * (k - 1)) / k
    if not picks:
        _card(page, xm, top, wm, 1.5, name="No testimonials")
        page.text(xm + 0.25, top + 0.3, wm - 0.5, 0.9,
                  Para("No customer feedback was retrieved in the saved research.", 13, MUTED,
                       after=0), pad=0.02, name="No testimonials text")
    for i, f in enumerate(picks):
        y = top + i * (qh + GAP)
        box(s, xm, y, wm, qh, fill=(TEAL_LIGHT, BLUE_LIGHT, GOLD_LIGHT)[i % 3],
            name=f"Quote card {i + 1}")
        icon(s, xm + 0.2, y + 0.2, 0.55, "speech", TEAL if f.kind == "praise" else BURGUNDY,
             name=f"Quote {i + 1}")
        quote, attribution = _split_quote(f.text)
        quote = _clause(quote, 150)
        page.text(xm + 0.9, y + 0.14, wm - 1.1, qh - 1.08,
                  Para(f"“{quote}”", 13, INK, italic=True, after=0), pad=0.02,
                  anchor=MSO_ANCHOR.MIDDLE, name=f"Quote: {f.competitor}")
        who = re.search(r"\bto ([A-Z][\w.’' -]{1,30}?)(?:,|\.|$)", attribution)
        basis = {"quoted": "quoted", "reported": "reported", "inferred": "inferred"}[f.basis]
        origin = _host(f.source_url) if f.source_url else "source not recorded"
        who_txt = f"{who.group(1)} · " if who else ""
        page.text(xm + 0.9, y + qh - 0.82, wm - 1.1, 0.74,
                  [Para(f"{f.competitor}", 11.5, INK, bold=True, after=0),
                   Para(f"{who_txt}{basis} on {origin}", 10.5, MUTED, after=0),
                   Para("Not independently verified", 10.5, MUTED, after=0)], pad=0.02,
                  name=f"Attribution: {f.competitor}")
    if len(findings) > len(picks):
        notes.append(f"{len(findings) - len(picks)} further testimonial(s) are in the saved report")

    # right: evidence availability and limits
    tile_h = 0.95
    for i, (label, value, color) in enumerate(
        (("Praise retrieved", str(praise), TEAL), ("Complaints retrieved", str(complaint),
                                                    BURGUNDY))
    ):
        y = top + i * (tile_h + 0.12)
        _card(page, xr, y, wr, tile_h, name=f"Evidence tile {i + 1}")
        box(s, xr, y, 0.09, tile_h, fill=color, round_=False, name="Accent")
        page.text(xr + 0.25, y + 0.06, 0.8, tile_h - 0.12,
                  Para(value, 32, color, bold=True, font=HEAD_FONT, after=0), pad=0.02,
                  anchor=MSO_ANCHOR.MIDDLE, name=f"Tile value {i + 1}")
        page.text(xr + 1.15, y + 0.06, wr - 1.3, tile_h - 0.12,
                  Para(label, 12.5, INK, bold=True, after=0), pad=0.02,
                  anchor=MSO_ANCHOR.MIDDLE, name=f"Tile label {i + 1}")
    y = top + 2 * (tile_h + 0.12)
    caveat = (
        "No complaints were retrieved. That is not evidence that customers have none."
        if complaint == 0 else
        f"{complaint} complaint(s) were retrieved; see the saved report."
    )
    ch_ = needed_height_in([Para(caveat, 12, INK, bold=True, after=0)], wr - 0.3, pad=0.12) + 0.1
    page.text(xr, y, wr, ch_, Para(caveat, 12, INK, bold=True, after=0), fill=GOLD_LIGHT,
              line=GOLD, pad=0.12, anchor=MSO_ANCHOR.MIDDLE, name="Complaint caveat")
    y += ch_ + 0.15
    limits = [_clause(g, 105) for g in ctx.source.reviews.gaps[:3]]
    bullets = limits or [_clause(b, 105) for b in spec.bullets[:2]]
    _heading(page, xr, y, wr, "Limits of the data", MUTED)
    page.text(xr, y + 0.32, wr, top + height - y - 0.34, _bullets(bullets, 11.5, INK, 4),
              pad=0.02, name="Limitations")
    page.finish(notes)


# ----------------------------------------------------------------------------- slide 4
def _slide_solution(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    st = ctx.source.strategy
    top, height = page.top, page.height
    notes: list[str] = []

    hero_h = 0.92
    box(s, MARGIN_X, top, CONTENT_W, hero_h, fill=BURGUNDY_LIGHT, name="Value proposition")
    chip(s, MARGIN_X + 0.25, top + hero_h / 2 - 0.17, "RECOMMENDATION", WHITE, BURGUNDY,
         size=11, h=0.34, name="Positioning tag", line=BURGUNDY)
    x0 = MARGIN_X + 0.25 + chip_width("RECOMMENDATION", 11) + 0.3
    positioning = _unlabel(st.positioning_line) or _unlabel(st.recommended_offer) or (
        "No positioning statement was recorded."
    )
    page.text(x0, top + 0.06, SLIDE_W - MARGIN_X - 0.25 - x0, hero_h - 0.12,
              Para(positioning, 19, INK, bold=True, font=HEAD_FONT, italic=True, after=0),
              pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name="Value proposition text")

    strip_h = 0.82
    fy = top + hero_h + 0.2
    fh = top + height - fy - strip_h - 0.15
    arrow_w = 0.36
    cw = (CONTENT_W - 3 * arrow_w) / 4
    observed = []
    for c in ctx.comps[:3]:
        row = next((r for r in st.comparison_matrix if r.get("competitor") == c.name), {})
        observed.append(f"{c.name}: {_clause(row.get('strength') or c.offer, 125)}")
    solution = [_clause(_unlabel(st.recommended_offer), 150)]
    why = _sentences(st.rationale)
    if why:
        solution.append(_clause(why[0], 130))
    gap_text = _clause(spec.bullets[0], 150) if spec.bullets else (
        _clause(st.market_gap, 150) or "No gap statement was recorded."
    )
    stages = (
        ("1", "Market evidence", "OBSERVED · PUBLIC PAGES", "chart", TEAL, TEAL_LIGHT,
         observed or ["No competitor findings were recorded."]),
        ("2", "Research-visible gap", "INFERENCE", "target", GOLD, GOLD_LIGHT,
         [gap_text, "An inference from this research, not a market size."]),
        ("3", "Proposed solution", "RECOMMENDATION", "star", BURGUNDY, BURGUNDY_LIGHT,
         [t for t in solution if t]),
        ("4", "How we differentiate", "RECOMMENDATION", "bolt", BLUE, BLUE_LIGHT,
         [_clause(b, 105) for b in spec.bullets[1:4]] or ["No differentiation was recorded."]),
    )
    for i, (num, title, tag, glyph, color, tint, items) in enumerate(stages):
        x = MARGIN_X + i * (cw + arrow_w)
        box(s, x, fy, cw, fh, fill=tint, name=f"Stage {num}")
        icon(s, x + 0.18, fy + 0.16, 0.56, glyph, color, name=f"Stage {num}")
        page.text(x + 0.85, fy + 0.2, cw - 1.0, 0.5,
                  Para(tag, 10, color, bold=True, after=0), pad=0.02,
                  anchor=MSO_ANCHOR.MIDDLE, name=f"Stage {num} tag")
        page.text(x + 0.18, fy + 0.8, cw - 0.36, 0.4,
                  Para(title, 15, INK, bold=True, font=HEAD_FONT, after=0), pad=0.02,
                  name=f"Stage {num} title")
        page.text(x + 0.18, fy + 1.28, cw - 0.36, fh - 1.38, _bullets(items, 12, INK, 5),
                  pad=0.02, name=f"Stage {num} text")
        if i < 3:
            arrow(s, x + cw + 0.03, fy + fh / 2, x + cw + arrow_w - 0.03, fy + fh / 2, color,
                  width_pt=3, name=f"Flow arrow {num}")

    sy = fy + fh + 0.15
    box(s, MARGIN_X, sy, CONTENT_W, strip_h, fill=PAPER, line=BORDER, name="Unknowns strip")
    page.text(MARGIN_X + 0.2, sy + 0.08, 1.7, strip_h - 0.16,
              [Para("STILL UNKNOWN", 10.5, MUTED, bold=True, after=0),
               Para("not assumed", 10.5, MUTED, after=0)], pad=0.02,
              anchor=MSO_ANCHOR.MIDDLE, name="Unknowns heading")
    unknown = [f"{n}: verified unit price and pack size" for n in ctx.unverified[:3]]
    for b in spec.bullets:
        if "unknown" in b.lower() and len(unknown) < 4:
            unknown.append(_clause(b, 70))
    _pills(page, MARGIN_X + 2.0, sy + 0.12, CONTENT_W - 2.2, unknown or ["Nothing flagged"],
           GOLD_LIGHT, GOLD, size=10.5, h=0.3, name="Unknown")
    notes.append("Framework: observed evidence, inferred gap, proposed solution, differentiation")
    page.finish(notes)


# ----------------------------------------------------------------------------- slide 5
def _slide_gtm(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    src, st = ctx.source, ctx.source.strategy
    top, height = page.top, page.height
    notes: list[str] = []
    plan = parse_weeks(ctx.deck.slides[5].bullets)

    # row 1: segment and positioning
    r1 = 1.25
    w1 = 4.8
    _card(page, MARGIN_X, top, w1, r1, name="Segment card")
    icon(s, MARGIN_X + 0.22, top + 0.3, 0.8, "person", TEAL, name="Segment")
    _heading(page, MARGIN_X + 1.22, top + 0.14, w1 - 1.4, "Target segment", TEAL)
    page.text(MARGIN_X + 1.22, top + 0.44, w1 - 1.4, r1 - 0.55,
              [Para(src.input.target_customer, 18, INK, bold=True, font=HEAD_FONT, after=1),
               Para(f"in {src.input.city}", 13, MUTED, bold=True, after=0)], pad=0.02,
              name="Segment")
    xp = MARGIN_X + w1 + GAP
    wp = CONTENT_W - w1 - GAP
    box(s, xp, top, wp, r1, fill=BURGUNDY_LIGHT, name="Positioning card")
    chip(s, xp + 0.25, top + 0.18, "RECOMMENDED POSITIONING", WHITE, BURGUNDY, size=10.5,
         h=0.32, name="Positioning recommendation tag", line=BURGUNDY)
    positioning = _unlabel(st.positioning_line) or "No positioning statement was recorded."
    page.text(xp + 0.25, top + 0.55, wp - 0.5, r1 - 0.62,
              Para(positioning, 17, INK, bold=True, italic=True, font=HEAD_FONT, after=0),
              pad=0.02, anchor=MSO_ANCHOR.MIDDLE, name="Positioning")

    # row 2: launch journey
    r3 = 1.2
    jy = top + r1 + 0.15
    jh = height - r1 - r3 - 0.3
    _card(page, MARGIN_X, jy, CONTENT_W, jh, name="Journey card")
    _heading(page, MARGIN_X + 0.25, jy + 0.12, 6, "Launch journey · recommended actions", TEAL)
    n = max(1, len(plan))
    colw = (CONTENT_W - 0.5) / n
    line_y = jy + 0.5
    box(s, MARGIN_X + 0.45, line_y + 0.26, CONTENT_W - 0.9, 0.05, fill=BORDER, round_=False,
        name="Journey path")
    if not plan:
        page.text(MARGIN_X + 0.3, jy + 0.6, 6, 0.4,
                  Para("No launch plan was recorded.", 13, MUTED, after=0), pad=0.02,
                  name="No plan")
    for i, (label, body) in enumerate(plan, 1):
        cx = MARGIN_X + 0.25 + (i - 1) * colw
        palette = (TEAL, BLUE, GOLD, BURGUNDY)
        color = palette[(i - 1) % 4]
        page.text(cx + 0.1, line_y, 0.56, 0.56, Para(str(i), 17, WHITE, bold=True,
                  font=HEAD_FONT, align=PP_ALIGN.CENTER, after=0), fill=color,
                  shape=MSO_SHAPE.OVAL, pad=0.0, anchor=MSO_ANCHOR.MIDDLE, wrap=False,
                  name=f"Journey stage {i}")
        page.text(cx + 0.78, line_y + 0.12, colw - 1.0, 0.3,
                  Para(label.upper(), 10.5, color, bold=True, after=0), pad=0.02,
                  name=f"Journey week {i}")
        parts = _clauses(body)
        head = _clause(parts[0], 110) if parts else _clause(body, 110)
        more = [_clause(p, 100) for p in parts[1:2]]
        page.text(cx + 0.1, line_y + 0.72, colw - 0.25, jh - 1.3,
                  [Para(head, 12.5, INK, bold=True, after=4)]
                  + [Para(m, 11.5, MUTED, after=3) for m in more], pad=0.02,
                  name=f"Journey action {i}")

    # row 3: observed vs dependencies
    ly = jy + jh + 0.15
    half = (CONTENT_W - GAP) / 2
    _card(page, MARGIN_X, ly, half, r3, name="Observed channels card")
    _heading(page, MARGIN_X + 0.2, ly + 0.1, half - 0.4,
             "Channels observed in the market · not a recommendation", BLUE)
    channels = sorted({ch for c in ctx.comps for ch in c.channels})
    observed: list[str] = []
    seen_keys: set[str] = set()
    for c in channels:
        label = _channel(c)
        key = label.lower().split()[0] if label.split() else label.lower()
        if key not in seen_keys:
            seen_keys.add(key)
            observed.append(label.split(" ordering")[0] if "whatsapp" in key else label)
    _pills(page, MARGIN_X + 0.2, ly + 0.5, half - 0.4, observed[:5] or ["None recorded"],
           BLUE_LIGHT, BLUE, size=10.5, h=0.3, name="Observed channel")
    xr = MARGIN_X + half + GAP
    _card(page, xr, ly, half, r3, name="Dependencies card")
    _heading(page, xr + 0.2, ly + 0.1, half - 0.4, "Depends on · before advertising", GOLD)
    deps = [_clause(t, 150) for t in _sentences(_unlabel(st.recommended_offer))[1:3]]
    for b in spec.bullets:
        if any(w in b.lower() for w in ("specify", "confirm")):
            deps.append(_clause(b, 150))
    page.text(xr + 0.2, ly + 0.4, half - 0.4, r3 - 0.44,
              _bullets(list(dict.fromkeys(deps))[:2] or ["None stated"], 11, INK, 2),
              pad=0.02,
              name="Dependencies")
    notes.append(f"Launch stages shown: {len(plan)}")
    page.finish(notes)


# ----------------------------------------------------------------------------- slide 6
def _slide_financials(page: Page) -> None:
    ctx, spec, s = page.ctx, page.spec, page.slide
    st = ctx.source.strategy
    top, height = page.top, page.height
    notes: list[str] = []
    wa, wb = 4.2, 4.3
    wc = CONTENT_W - wa - wb - 2 * GAP
    xa, xb, xc = MARGIN_X, MARGIN_X + wa + GAP, MARGIN_X + wa + wb + 2 * GAP

    # A: recommended test price hero
    box(s, xa, top, wa, height, fill=INK, name="Price hero")
    page.text(xa + 0.3, top + 0.2, wa - 0.6, 0.3,
              Para("RECOMMENDED TEST PRICE", 11, TEAL_ON_INK, bold=True, after=0), pad=0.02,
              name="Price eyebrow")
    head, plan, derived, note = _price_parts(st.recommended_price)
    y = top + 0.6
    if head:
        page.text(xa + 0.3, y, wa - 0.6, 1.1,
                  Para(head, 54, GOLD_LIGHT, bold=True, font=HEAD_FONT, after=0), pad=0.02,
                  anchor=MSO_ANCHOR.MIDDLE, name="Price value")
        y += 1.2
        lines = []
        if plan:
            lines.append(Para(plan, 15, WHITE, bold=True, after=4))
        if derived:
            lines.append(Para(derived[:1].upper() + derived[1:], 13, TEAL_ON_INK, after=4))
        if note:
            lines.append(Para(_clause(note, 110), 12, WHITE, after=12))
    else:
        lines = [Para(_clause(st.recommended_price, 140) or "No price recommendation.", 14,
                      WHITE, after=0)]
    warn = [Para("RECOMMENDATION — NOT A VERIFIED MARKET PRICE", 10.5, GOLD, bold=True,
                 after=0)]
    wh = needed_height_in(warn, wa - 0.6, pad=0.1) + 0.06
    wy = top + height - wh - 0.25
    open_items = [_clause(t, 110) for t in _sentences(st.rationale)[:3]]
    lines = lines + [Para("OPEN ASSUMPTIONS", 10.5, TEAL_ON_INK, bold=True, after=3)] + [
        Para(i, 11.5, WHITE, bullet=True, after=4) for i in open_items
    ]
    page.text(xa + 0.3, y, wa - 0.6, max(0.4, wy - y - 0.1), lines, pad=0.02,
              name="Price detail")
    page.text(xa + 0.3, wy, wa - 0.6, wh, warn, fill=GOLD_LIGHT, line=GOLD, pad=0.1,
              anchor=MSO_ANCHOR.MIDDLE, name="Price warning")

    # B: competitor price evidence (not comparable)
    _card(page, xb, top, wb, height, name="Price evidence card")
    _heading(page, xb + 0.2, top + 0.16, wb - 0.4, "Competitor price evidence", GOLD)
    n = max(1, len(ctx.comps))
    rows_h = height - 1.75
    rh = min(1.55, rows_h / n)
    y = top + 0.55
    for c in ctx.comps:
        verified = c.price.status == "verified" and c.price.amount is not None
        tag = "VERIFIED" if verified else "NOT VERIFIED"
        tw = chip_width(tag, 10)
        box(s, xb + 0.2, y, wb - 0.4, rh - 0.1, fill=TEAL_LIGHT if verified else GOLD_LIGHT,
            name=f"Price evidence: {c.name}")
        mention = _clause(c.unknowns[0], 120) if c.unknowns else "No price evidence recorded."
        if rh >= 1.0:
            page.text(xb + 0.35, y + 0.08, wb - 0.7 - tw - 0.1, 0.34,
                      Para(c.name, 13.5, INK, bold=True, font=HEAD_FONT, after=0), pad=0.02,
                      name=f"Price name: {c.name}")
            chip(s, xb + wb - 0.35 - tw, y + 0.1, tag, WHITE, TEAL if verified else GOLD,
                 size=10, h=0.3, name=f"Price status: {c.name}",
                 line=TEAL if verified else GOLD)
            page.text(xb + 0.35, y + 0.46, wb - 0.7, rh - 0.64,
                      Para(mention, 11.5, INK, after=0), pad=0.02,
                      name=f"Price mention: {c.name}")
        else:
            chip(s, xb + wb - 0.35 - tw, y + (rh - 0.1 - 0.3) / 2, tag, WHITE,
                 TEAL if verified else GOLD, size=10, h=0.3,
                 name=f"Price status: {c.name}", line=TEAL if verified else GOLD)
            page.text(xb + 0.35, y + 0.03, wb - 0.7 - tw - 0.15, rh - 0.16,
                      [Para(c.name, 11.5, INK, bold=True, after=0)], pad=0.02,
                      anchor=MSO_ANCHOR.MIDDLE, name=f"Price name: {c.name}")
        y += rh
    page.text(xb + 0.2, top + height - 1.0, wb - 0.4, 0.82,
              Para("These mentions have no verified unit or pack size, so they are not "
                   "comparable with the recommended test price.", 11.5, MUTED, italic=True,
                   after=0), pad=0.02, name="Comparability note")

    # C: decision checkpoints
    _card(page, xc, top, wc, height, name="Checkpoints card")
    _heading(page, xc + 0.2, top + 0.16, wc - 0.4, "Decision checkpoints", BURGUNDY)
    weeks = parse_weeks(spec.bullets)
    points: list[tuple[str, str]] = []
    for label, body in weeks:
        for part in _clauses(body):
            if any(v in part.lower() for v in ("validate", "track", "review", "measure")):
                points.append((label, _clause(part, 110)))
                break
    if not points and weeks:
        points = [(label, _clause(body, 110)) for label, body in weeks[:3]]
    ph = (height - 0.6) / max(1, len(points))
    for i, (label, clause) in enumerate(points[:4]):
        y = top + 0.55 + i * ph
        page.text(xc + 0.2, y + 0.05, 0.56, 0.56,
                  Para(label.split()[-1], 16, WHITE, bold=True, font=HEAD_FONT,
                       align=PP_ALIGN.CENTER, after=0), fill=BURGUNDY, shape=MSO_SHAPE.OVAL,
                  pad=0.0, anchor=MSO_ANCHOR.MIDDLE, wrap=False, name=f"Checkpoint {i + 1}")
        page.text(xc + 0.9, y, wc - 1.1, ph - 0.1,
                  [Para(label.upper(), 10, BURGUNDY, bold=True, after=1),
                   Para(clause[:1].upper() + clause[1:], 12, INK, after=0)], pad=0.02,
                  anchor=MSO_ANCHOR.MIDDLE, name=f"Checkpoint text {i + 1}")
    notes.append("Checkpoints are the plan's validate / track / review actions, by week")
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
