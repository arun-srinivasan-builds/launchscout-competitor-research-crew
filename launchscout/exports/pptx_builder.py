"""Render a `DeckSpec` as an enterprise-style, fully editable six-slide PowerPoint.

Slides are composed from native shapes, text boxes, connectors and one native chart (no flattened
images). The only picture is the approved LS logo. Layout is content-agnostic: numbers and text
come from the saved research (`DeckSource`) and the validated `DeckSpec`; nothing is hardcoded
to one business idea, and missing evidence is shown as missing, never filled in.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from launchscout.exports.pptx_components import (
    AMBER,
    AMBER_DARK,
    BLUE,
    BORDER,
    CONTENT_BOTTOM,
    CONTENT_W,
    FOOTER_TOP,
    GAP,
    LINE_SPACING,
    MARGIN_X,
    MUTED,
    NAVY,
    PURPLE,
    PURPLE_DARK,
    SLIDE_H,
    SLIDE_W,
    SOFT_WHITE,
    SURFACE,
    SURFACE_2,
    TEAL,
    TEAL_DARK,
    TEXT,
    Para,
    arrow,
    badge,
    box,
    chip,
    chip_width,
    estimate_lines,
    kpi_tile,
    needed_height_in,
    panel,
    split_widths,
)
from launchscout.exports.pptx_components import text as text_box
from launchscout.schemas import Competitor, DeckSpec, SlideSpec

if TYPE_CHECKING:
    from launchscout.deck import DeckSource

LOGO_FILE = Path(__file__).resolve().parent.parent.parent / "static" / "ls_logo_transparent.png"
LOGO_ASPECT = 691 / 623
GATE_MIN = 3  # mirrors validation.evaluate_gate (3 evidence-backed competitors, 3 verified prices)
KICKERS = (
    "EXECUTIVE DASHBOARD",
    "COMPARISON MATRIX",
    "EVIDENCE INTELLIGENCE",
    "OPPORTUNITY MAP",
    "PRICING STRATEGY",
    "VISUAL ROADMAP",
)
_AMOUNT = re.compile(r"(₹|Rs\.?|INR|\$|USD|€|EUR)\s?(\d[\d,]*(?:\.\d+)?)", re.I)
_WEEK = re.compile(r"^\s*week\s*(\d+)\s*[:\-–—]\s*(.+)$", re.I | re.S)
_ACCESS = re.compile(
    r"could not|cannot|not readable|unreadable|unavailable|blocked|login|not retriev", re.I
)
_FOOTER_NAMES = ("Footer", "Footer rule", "Slide number")


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
    """Drop a leading 'Recommendation:' (the slide's tag already says it) and wrapping quotes."""
    cleaned = re.sub(r"^\s*recommendation\s*:\s*", "", value or "", flags=re.I).strip()
    cleaned = cleaned.strip("\"'“”‘’ ")
    return cleaned[:1].upper() + cleaned[1:]


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

    def findings(self, competitor: str, kind: str) -> list:
        key = competitor.casefold().strip()
        return [
            f
            for f in self.source.reviews.findings
            if f.competitor.casefold().strip() == key and f.kind == kind
        ]


# ----------------------------------------------------------------------------- chrome
def _chrome(prs, ctx: Ctx, index: int, spec: SlideSpec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = NAVY

    box(slide, MARGIN_X, 0.3, 1.0, 0.8, fill=SOFT_WHITE, name="LS logo tile")
    pic_h = 0.62
    pic_w = pic_h * LOGO_ASPECT
    pic = slide.shapes.add_picture(
        str(LOGO_FILE), Inches(MARGIN_X + (1.0 - pic_w) / 2), Inches(0.39), height=Inches(pic_h)
    )
    pic.name = "LS logo"
    pic._element.nvPicPr.cNvPr.set("descr", "LaunchScout LS logo")

    text_box(
        slide,
        1.72,
        0.26,
        7.5,
        0.27,
        Para(f"{index:02d}  ·  {KICKERS[index - 1]}", 12, TEAL, bold=True, after=0),
        pad=0.02,
        name="Kicker",
    )
    text_box(
        slide,
        1.72,
        0.54,
        8.6,
        0.62,
        Para(spec.title, 30, TEXT, bold=True, after=0),
        pad=0.02,
        anchor=MSO_ANCHOR.MIDDLE,
        name="Title",
    )
    status_fill = AMBER_DARK if ctx.source.partial else TEAL_DARK
    status_color = AMBER if ctx.source.partial else TEAL
    label = f"●  {ctx.status_label}"
    width = chip_width(label, 12)
    chip(
        slide,
        SLIDE_W - MARGIN_X - width,
        0.52,
        label,
        status_fill,
        status_color,
        size=12,
        h=0.36,
        name="Evidence status",
        line=status_color,
    )

    top = 1.3
    if spec.labels:
        paras = [Para("   ·   ".join(spec.labels), 12, AMBER, bold=True, after=0)]
        h = needed_height_in(paras, CONTENT_W, pad=0.12) + 0.04
        text_box(
            slide,
            MARGIN_X,
            top,
            CONTENT_W,
            h,
            paras,
            fill=AMBER_DARK,
            pad=0.12,
            anchor=MSO_ANCHOR.MIDDLE,
            name="Labels",
        )
        top += h + 0.14

    arrow(
        slide,
        MARGIN_X,
        FOOTER_TOP,
        SLIDE_W - MARGIN_X,
        FOOTER_TOP,
        BORDER,
        width_pt=1.0,
        head=False,
        name="Footer rule",
    )
    footer = (
        f"LaunchScout  ·  {ctx.source.input.idea}  ·  {ctx.source.input.city}  ·  "
        f"{'partial evidence' if ctx.source.partial else 'validated report'}  ·  "
        f"run {ctx.source.run_id}  ·  generated {ctx.generated_on.isoformat()}"
    )
    text_box(
        slide,
        MARGIN_X,
        FOOTER_TOP + 0.04,
        CONTENT_W - 1.1,
        0.4,
        Para(footer, 10, MUTED, after=0),
        pad=0.02,
        name="Footer",
    )
    text_box(
        slide,
        SLIDE_W - MARGIN_X - 1.0,
        FOOTER_TOP + 0.04,
        1.0,
        0.3,
        Para(f"{index} / 6", 11, TEAL, bold=True, align=PP_ALIGN.RIGHT, after=0),
        pad=0.02,
        name="Slide number",
    )
    return slide, top


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


# ----------------------------------------------------------------------------- slide 1
def _slide_dashboard(prs, ctx: Ctx, index: int, spec: SlideSpec) -> None:
    slide, top = _chrome(prs, ctx, index, spec)
    src = ctx.source
    kpi_h = max(1.1, min(1.65, (CONTENT_BOTTOM - top - GAP) * 0.42))
    n = len(ctx.comps)
    tiles = [
        (str(n), "Competitors researched", "named competitors with a URL and offer", TEAL),
        (
            str(ctx.n_evidence),
            "Evidence-backed",
            f"with at least one evidence page ({GATE_MIN} needed to pass)",
            TEAL if ctx.n_evidence >= GATE_MIN else AMBER,
        ),
        (
            str(ctx.n_verified),
            "Verified prices",
            f"amount, unit, source and date ({GATE_MIN} needed to pass)",
            TEAL if ctx.n_verified >= GATE_MIN else AMBER,
        ),
        (
            "PARTIAL" if src.partial else "PASSED",
            "Research acceptance",
            "report failed the acceptance gate; every slide is labelled"
            if src.partial
            else "all acceptance checks passed",
            AMBER if src.partial else TEAL,
        ),
    ]
    x = MARGIN_X
    for (value, label, caption, accent), w in zip(tiles, split_widths(CONTENT_W, 4), strict=True):
        kpi_tile(slide, x, top, w, kpi_h, value, label, caption, accent)
        x += w + GAP
    y = top + kpi_h + GAP
    h = CONTENT_BOTTOM - y
    w1, w2 = 4.7, 4.1
    w3 = CONTENT_W - w1 - w2 - 2 * GAP

    inner = panel(slide, MARGIN_X, y, w1, h, "Business opportunity", accent=TEAL)
    rows = [
        ("I", "Idea", src.input.idea),
        ("M", "Market", src.input.city),
        ("C", "Customer", src.input.target_customer),
        ("H", "Opportunity (assumption)", _short(src.strategy.market_gap, 190) or "Not stated"),
    ]
    text_w = w1 - 0.85
    needs = [
        needed_height_in(
            [Para(label.upper(), 11, MUTED, bold=True, after=1), Para(value, 14, TEXT, after=0)],
            text_w,
            pad=0.03,
        )
        + 0.04
        for _, label, value in rows
    ]
    end = y + h - 0.1
    spare = max(0.0, end - inner - sum(needs[:3]) - 1.0)  # keep >= 1in for the hypothesis
    ry = inner
    for i, (glyph, label, value) in enumerate(rows):
        row_h = needs[i] + spare / 3 if i < 3 else end - ry
        badge(slide, MARGIN_X + 0.2, ry + 0.06, 0.38, glyph, TEAL if i < 3 else PURPLE, size=13)
        text_box(
            slide,
            MARGIN_X + 0.7,
            ry,
            w1 - 0.85,
            row_h - 0.04,
            [Para(label.upper(), 11, MUTED, bold=True, after=1), Para(value, 14, TEXT, after=0)],
            pad=0.03,
            name=f"Opportunity {label.split()[0]}",
        )
        ry += row_h

    x2 = MARGIN_X + w1 + GAP
    inner2 = panel(slide, x2, y, w2, h, "Acceptance gate progress", accent=BLUE)
    data = CategoryChartData()
    data.categories = ["Evidence-backed competitors", "Verified prices"]
    data.add_series("Achieved", (ctx.n_evidence, ctx.n_verified))
    data.add_series("Required to pass", (GATE_MIN, GATE_MIN))
    frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(x2 + 0.15),
        Inches(inner2),
        Inches(w2 - 0.3),
        Inches(y + h - inner2 - 0.1),
        data,
    )
    frame.name = "Gate progress chart"
    chart = frame.chart
    chart.font.size = Pt(11)
    chart.font.name = "Calibri"
    chart.font.color.rgb = TEXT
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.color.rgb = TEXT
    chart.value_axis.maximum_scale = max(GATE_MIN, ctx.n_evidence, ctx.n_verified)
    chart.value_axis.minimum_scale = 0
    chart.value_axis.major_unit = 1
    chart.value_axis.has_major_gridlines = False
    chart.value_axis.tick_labels.font.color.rgb = MUTED
    chart.category_axis.tick_labels.font.color.rgb = TEXT
    plot = chart.plots[0]
    for series, color in zip(plot.series, (AMBER if src.partial else TEAL, BORDER), strict=True):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = color
    plot.has_data_labels = True
    plot.data_labels.font.color.rgb = TEXT
    plot.data_labels.font.bold = True
    plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    plot.gap_width = 60

    x3 = x2 + w2 + GAP
    title = "Why it is partial" if src.partial else "Evidence summary"
    inner3 = panel(slide, x3, y, w3, h, title, accent=AMBER if src.partial else TEAL)
    reasons = src.acceptance_reasons or ["All acceptance checks passed."]
    cleaned = [re.sub(r"^R\d\s+", "", r) for r in reasons]
    paras = [Para(_short(r, 130), 12, TEXT, bullet=True, after=6) for r in cleaned[:4]]
    text_box(
        slide,
        x3 + 0.18,
        inner3,
        w3 - 0.3,
        y + h - inner3 - 0.1,
        paras,
        pad=0.03,
        name="Acceptance reasons",
    )
    _notes(slide, spec, [f"Acceptance reason: {r}" for r in reasons])


# ----------------------------------------------------------------------------- slide 2
ROW_SPEC = (
    ("O", "Offering", 0.95),
    ("S", "Subscription", 0.65),
    ("C", "Channels", 0.5),
    ("$", "Pricing", 0.95),
    ("E", "Evidence", 0.5),
    ("!", "Limitations", 0.9),
)


def _subscription_text(comp: Competitor) -> str:
    hits = [
        s for s in _sentences(comp.offer) if re.search(r"subscri|plan|weekly|daily|trial", s, re.I)
    ]
    return " ".join(hits) if hits else "Not evidenced in the research"


def _slide_matrix(prs, ctx: Ctx, index: int, spec: SlideSpec) -> None:
    slide, top = _chrome(prs, ctx, index, spec)
    comps = ctx.comps[:5]
    if not comps:
        text_box(
            slide,
            MARGIN_X,
            top + 0.3,
            CONTENT_W,
            1.0,
            Para("No competitors with evidence were recorded for this run.", 18, MUTED),
            fill=SURFACE,
            line=BORDER,
            name="No competitors",
        )
        _notes(slide, spec, [])
        return
    label_w = 1.75
    col_ws = split_widths(CONTENT_W - label_w - 0.1, len(comps), 0.1)
    header_h = 0.62
    gap = 0.1
    avail = CONTENT_BOTTOM - top - header_h - gap
    total_w = sum(r[2] for r in ROW_SPEC)
    heights = [(avail - gap * (len(ROW_SPEC) - 1)) * r[2] / total_w for r in ROW_SPEC]
    x = MARGIN_X + label_w + gap
    for comp, w in zip(comps, col_ws, strict=True):
        text_box(
            slide,
            x,
            top,
            w,
            header_h,
            [
                Para(comp.name, 17, TEXT, bold=True, after=0),
                Para(_host(comp.url), 11, MUTED, after=0),
            ],
            fill=SURFACE_2,
            line=TEAL,
            anchor=MSO_ANCHOR.MIDDLE,
            pad=0.1,
            name=f"Competitor {comp.name}",
        )
        x += w + gap
    y = top + header_h + gap
    for (glyph, label, _), h in zip(ROW_SPEC, heights, strict=True):
        box(slide, MARGIN_X, y, label_w, h, fill=SURFACE, line=BORDER, name="Row label panel")
        badge(slide, MARGIN_X + 0.12, y + (h - 0.36) / 2, 0.36, glyph, TEAL, size=12)
        text_box(
            slide,
            MARGIN_X + 0.55,
            y,
            label_w - 0.6,
            h,
            Para(label, 13, TEXT, bold=True, after=0),
            pad=0.03,
            anchor=MSO_ANCHOR.MIDDLE,
            name=f"Row {label}",
        )
        x = MARGIN_X + label_w + gap
        for comp, w in zip(comps, col_ws, strict=True):
            verified = comp.price.status == "verified"
            fill, line = SURFACE, BORDER
            if label == "Offering":
                paras = [Para(comp.offer or "Not evidenced", 13)]
            elif label == "Subscription":
                paras = [Para(_subscription_text(comp), 13)]
            elif label == "Channels":
                paras = [Para(", ".join(comp.channels) or "Not evidenced", 13)]
            elif label == "Pricing" and verified:
                p = comp.price
                paras = [
                    Para("●  VERIFIED", 11, TEAL, bold=True, after=1),
                    Para(f"{p.currency} {p.amount:g} per {p.unit}", 14, TEXT, bold=True),
                ]
                fill, line = TEAL_DARK, TEAL
            elif label == "Pricing":
                paras = [
                    Para("●  NOT VERIFIED", 11, AMBER, bold=True, after=1),
                    Para("Price unknown", 14, TEXT, bold=True),
                ]
                fill, line = AMBER_DARK, AMBER
            elif label == "Evidence":
                hosts = ", ".join(dict.fromkeys(_host(u) for u in comp.evidence_urls)) or "none"
                paras = [Para(f"{len(comp.evidence_urls)} source page(s): {hosts}", 12)]
            else:
                items = comp.unknowns[:2] or ["None recorded"]
                paras = [Para(i, 12, TEXT, bullet=True, after=2) for i in items]
            text_box(
                slide,
                x,
                y,
                w,
                h,
                paras,
                fill=fill,
                line=line,
                anchor=MSO_ANCHOR.MIDDLE,
                pad=0.1,
                name=f"{label}: {comp.name}",
            )
            x += w + gap
        y += h + gap
    extra = [
        f"{c.name}: offer={c.offer}; channels={', '.join(c.channels) or 'n/a'}; "
        f"price={c.price.status}; unknowns={'; '.join(c.unknowns) or 'none'}"
        for c in comps
    ]
    _notes(slide, spec, extra)


# ----------------------------------------------------------------------------- slide 3
def _state_cell(slide, x, y, w, h, label: str, good: bool, name: str) -> None:
    fill, line, color = (TEAL_DARK, TEAL, TEAL) if good else (AMBER_DARK, AMBER, AMBER)
    text_box(
        slide,
        x,
        y,
        w,
        h,
        Para(label, 12, color, bold=True, align=PP_ALIGN.CENTER, after=0),
        fill=fill,
        line=line,
        anchor=MSO_ANCHOR.MIDDLE,
        pad=0.04,
        name=name,
    )


def _slide_evidence(prs, ctx: Ctx, index: int, spec: SlideSpec) -> None:
    slide, top = _chrome(prs, ctx, index, spec)
    comps = ctx.comps[:5]
    right_w = 5.05
    left_w = CONTENT_W - right_w - GAP
    avail = CONTENT_BOTTOM - top
    inner = panel(
        slide, MARGIN_X, top, left_w, avail, "Evidence coverage by competitor", accent=BLUE
    )
    cols = ["Offer", "Channels", "Price", "Praise", "Pain points", "Pages"]
    name_w = 1.5
    cell_w = (left_w - 0.3 - name_w - GAP * len(cols)) / len(cols)
    x0 = MARGIN_X + 0.18
    for i, col in enumerate(cols):
        text_box(
            slide,
            x0 + name_w + GAP + i * (cell_w + GAP),
            inner,
            cell_w,
            0.5,
            Para(col.upper(), 10, MUTED, bold=True, align=PP_ALIGN.CENTER, after=0),
            pad=0.02,
            name=f"Column {col}",
        )
    rows = max(1, len(comps))
    grid_top = inner + 0.56
    legend_h = 0.4
    row_h = min(1.5, (top + avail - grid_top - legend_h - 0.1 - GAP * (rows - 1)) / rows)
    for r, comp in enumerate(comps):
        y = grid_top + r * (row_h + GAP)
        text_box(
            slide,
            x0,
            y,
            name_w,
            row_h,
            Para(comp.name, 13, TEXT, bold=True, after=0),
            pad=0.04,
            anchor=MSO_ANCHOR.MIDDLE,
            name=f"Coverage {comp.name}",
        )
        praise = ctx.findings(comp.name, "praise")
        complaints = ctx.findings(comp.name, "complaint")
        verified = comp.price.status == "verified"
        cells = [
            ("Yes" if comp.offer else "None", bool(comp.offer)),
            ("Yes" if comp.channels else "None", bool(comp.channels)),
            ("Verified" if verified else "Unknown", verified),
            (f"{len(praise)} found" if praise else "None", bool(praise)),
            (f"{len(complaints)} found" if complaints else "None found", bool(complaints)),
            (f"{len(comp.evidence_urls)}", bool(comp.evidence_urls)),
        ]
        for i, (label, good) in enumerate(cells):
            _state_cell(
                slide,
                x0 + name_w + GAP + i * (cell_w + GAP),
                y,
                cell_w,
                row_h,
                label,
                good,
                f"{cols[i]}: {comp.name}",
            )
    ly = top + avail - legend_h
    chip(slide, x0, ly, "SUPPORTED", TEAL_DARK, TEAL, size=11, line=TEAL, name="Legend supported")
    chip(
        slide,
        x0 + 1.4,
        ly,
        "UNKNOWN / NOT RETRIEVED",
        AMBER_DARK,
        AMBER,
        size=11,
        line=AMBER,
        name="Legend unknown",
    )

    supported = [f for f in ctx.source.reviews.findings if f.basis in ("quoted", "reported")]
    vendor_only = bool(supported) and all(
        any(_host(f.source_url or "") == _host(c.url) for c in ctx.comps) for f in supported
    )
    complaints_total = sum(1 for f in ctx.source.reviews.findings if f.kind == "complaint")
    access = [u for c in ctx.comps for u in c.unknowns if _ACCESS.search(u)]
    access += [g for g in ctx.source.reviews.gaps if _ACCESS.search(g)]
    unverified: list[str] = []
    if vendor_only:
        unverified.append(
            "All retrieved praise is published on the vendor's own site; independent "
            "verification is unknown."
        )
    if complaints_total == 0:
        unverified.append("No verifiable customer complaints were retrieved.")
    unverified += [
        _short(g, 80)
        for g in ctx.source.reviews.gaps
        if g not in access and not (complaints_total == 0 and re.search(r"complaint", g, re.I))
    ][:1]
    unverified = unverified[:2]
    validation = []
    if complaints_total == 0:
        validation.append("Gather independent reviews or run customer interviews.")
    if ctx.unverified:
        validation.append("Confirm unit price and pack size directly with each vendor.")
    validation.append("Capture first-hand feedback during the proposed pilot.")
    quoted = sum(1 for f in supported if f.basis == "quoted")
    cards = [
        (
            "Supported claims",
            TEAL,
            [f"{len(supported)} customer comment(s) with a source URL ({quoted} quoted)"]
            if supported
            else ["No customer comments with a source were retrieved."],
        ),
        ("Unverified", AMBER, unverified or ["Nothing flagged beyond the gaps shown."]),
        (
            "Source-access limits",
            PURPLE,
            [_short(a, 100) for a in dict.fromkeys(access)][:2]
            or ["No access problems were recorded."],
        ),
        ("Recommended validation (not yet done)", BLUE, validation),
    ]
    overhead = 0.52  # panel heading band plus bottom padding
    texts = [
        needed_height_in(
            [Para(line, 12, TEXT, bullet=True, after=2) for line in lines], right_w - 0.3, pad=0.03
        )
        for _, _, lines in cards
    ]
    card_gap = 0.1
    room = avail - card_gap * 3 - overhead * len(cards)
    small = [t for t in texts if t <= 0.4]  # single-line cards keep exactly what they need
    big_total = sum(t for t in texts if t > 0.4) or 1.0
    scale = (room - sum(small)) / big_total  # big cards grow into spare space or shrink evenly
    heights = [overhead + (t if t <= 0.4 else t * scale) for t in texts]
    rx = MARGIN_X + left_w + GAP
    y = top
    for (heading, accent, lines), h in zip(cards, heights, strict=True):
        ti = panel(slide, rx, y, right_w, h, heading, accent=accent)
        text_box(
            slide,
            rx + 0.18,
            ti,
            right_w - 0.3,
            y + h - ti - 0.06,
            [Para(line, 12, TEXT, bullet=True, after=2) for line in lines],
            pad=0.03,
            name=f"Card {heading}",
        )
        y += h + card_gap
    _notes(slide, spec, [f"{f.competitor} ({f.basis}): {f.text}" for f in supported])


# ----------------------------------------------------------------------------- slide 4
def _slide_flow(prs, ctx: Ctx, index: int, spec: SlideSpec) -> None:
    slide, top = _chrome(prs, ctx, index, spec)
    s = ctx.source.strategy
    observed = [
        f"{c.name}: {_short((_sentences(c.offer) or [c.offer])[0] or 'offer not evidenced', 85)}"
        for c in ctx.comps[:4]
    ] or ["No competitor findings recorded."]
    gaps: list[str] = []
    if ctx.unverified:
        gaps.append("Price not verified: " + ", ".join(ctx.unverified[:4]))
    gaps += [_short(g, 90) for g in ctx.source.reviews.gaps[:2]]
    for c in ctx.comps:
        gaps += [_short(u, 80) for u in c.unknowns[:1]]
    gaps = list(dict.fromkeys(gaps))[:4] or ["No gaps recorded."]
    hypothesis = [_short(s.market_gap, 230) or "No market gap was stated."]
    if s.rationale:
        hypothesis.append(_short(s.rationale, 130))
    diff = [_unlabel(d) for d in (s.recommended_offer, s.positioning_line) if d]
    stages = [
        (
            "1  OBSERVED",
            "Competitor characteristics",
            "VERIFIED FINDINGS",
            TEAL,
            TEAL_DARK,
            observed,
        ),
        (
            "2  EVIDENCE GAPS",
            "What research could not confirm",
            "RESEARCH LIMITATIONS",
            AMBER,
            AMBER_DARK,
            gaps,
        ),
        ("3  OPPORTUNITY", "Hypothesis from the gaps", "ASSUMPTION", BLUE, SURFACE_2, hypothesis),
        (
            "4  DIFFERENTIATION",
            "Proposed response",
            "RECOMMENDATION",
            PURPLE,
            PURPLE_DARK,
            [_short(d, 200) for d in diff] or ["No recommendation recorded."],
        ),
    ]
    legend_h = 0.42
    avail = CONTENT_BOTTOM - top - legend_h - GAP
    arrow_w = 0.42
    w = (CONTENT_W - 3 * arrow_w) / 4
    x = MARGIN_X
    for i, (head, sub, tag, accent, fill, lines) in enumerate(stages):
        box(slide, x, top, w, avail, fill=fill, line=accent, line_w=1.5, name=f"Stage {i + 1}")
        text_box(
            slide,
            x + 0.12,
            top + 0.1,
            w - 0.24,
            0.34,
            Para(head, 14, accent, bold=True, after=0),
            pad=0.02,
            name=f"Stage {i + 1} heading",
        )
        text_box(
            slide,
            x + 0.12,
            top + 0.44,
            w - 0.24,
            0.32,
            Para(sub, 12, MUTED, after=0),
            pad=0.02,
            name=f"Stage {i + 1} subtitle",
        )
        chip(
            slide,
            x + 0.12,
            top + 0.82,
            tag,
            NAVY,
            accent,
            size=11,
            line=accent,
            name=f"Stage {i + 1} tag",
        )
        text_box(
            slide,
            x + 0.12,
            top + 1.22,
            w - 0.24,
            avail - 1.32,
            [Para(line, 14, TEXT, bullet=i < 2, after=8) for line in lines],
            pad=0.04,
            name=f"Stage {i + 1} content",
        )
        if i < 3:
            ax = x + w + 0.04
            arrow(
                slide,
                ax,
                top + avail / 2,
                ax + arrow_w - 0.08,
                top + avail / 2,
                TEAL,
                width_pt=3.0,
                name=f"Flow arrow {i + 1}",
            )
        x += w + arrow_w
    ly = CONTENT_BOTTOM - legend_h
    lx = MARGIN_X
    for label, accent, fill in (
        ("VERIFIED FINDING", TEAL, TEAL_DARK),
        ("RESEARCH LIMITATION", AMBER, AMBER_DARK),
        ("ASSUMPTION", BLUE, SURFACE_2),
        ("RECOMMENDATION", PURPLE, PURPLE_DARK),
    ):
        _, cw = chip(
            slide,
            lx,
            ly + 0.05,
            label,
            fill,
            accent,
            size=11,
            line=accent,
            name=f"Legend {label.title()}",
        )
        lx += cw + 0.2
    text_box(
        slide,
        lx + 0.1,
        ly,
        SLIDE_W - MARGIN_X - lx - 0.1,
        legend_h,
        Para(
            "A hypothesis, not a proven fact.",
            12,
            MUTED,
            italic=True,
            after=0,
        ),
        pad=0.03,
        anchor=MSO_ANCHOR.MIDDLE,
        name="Flow caveat",
    )
    _notes(slide, spec, observed + gaps + hypothesis + diff)


# ----------------------------------------------------------------------------- slide 5
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


def _slide_pricing(prs, ctx: Ctx, index: int, spec: SlideSpec) -> None:
    slide, top = _chrome(prs, ctx, index, spec)
    s = ctx.source.strategy
    avail = CONTENT_BOTTOM - top
    hero_w = 4.9
    headline, plan, derived, note = _price_parts(s.recommended_price)
    box(
        slide,
        MARGIN_X,
        top,
        hero_w,
        avail,
        fill=PURPLE_DARK,
        line=PURPLE,
        line_w=2.0,
        name="Price hero",
    )
    text_box(
        slide,
        MARGIN_X + 0.15,
        top + 0.15,
        hero_w - 0.3,
        0.62,
        Para(
            "RECOMMENDATION — NOT A VERIFIED MARKET PRICE",
            13,
            AMBER,
            bold=True,
            align=PP_ALIGN.CENTER,
            after=0,
        ),
        fill=AMBER_DARK,
        line=AMBER,
        anchor=MSO_ANCHOR.MIDDLE,
        pad=0.08,
        name="Price warning",
    )
    text_box(
        slide,
        MARGIN_X + 0.15,
        top + 0.95,
        hero_w - 0.3,
        1.3,
        Para(
            headline or "No price",
            66 if headline else 30,
            TEXT,
            bold=True,
            align=PP_ALIGN.CENTER,
            after=0,
        ),
        anchor=MSO_ANCHOR.MIDDLE,
        pad=0.02,
        name="Price value",
    )
    y = top + 2.3
    if plan:
        text_box(
            slide,
            MARGIN_X + 0.2,
            y,
            hero_w - 0.4,
            0.75,
            Para(plan, 17, TEXT, bold=True, align=PP_ALIGN.CENTER, after=0),
            pad=0.03,
            anchor=MSO_ANCHOR.MIDDLE,
            name="Plan description",
        )
        y += 0.85
    if derived:
        text_box(
            slide,
            MARGIN_X + 0.4,
            y,
            hero_w - 0.8,
            0.62,
            [
                Para("DERIVED CALCULATION", 10, MUTED, bold=True, align=PP_ALIGN.CENTER, after=0),
                Para(
                    derived[:1].upper() + derived[1:],
                    14,
                    BLUE,
                    bold=True,
                    align=PP_ALIGN.CENTER,
                    after=0,
                ),
            ],
            fill=SURFACE,
            line=BLUE,
            anchor=MSO_ANCHOR.MIDDLE,
            pad=0.05,
            name="Derived calc",
        )
        y += 0.78
    foot = (
        note[:1].upper() + note[1:]
        if note
        else ("Proposed test price only; not validated with customers.")
    )
    if ctx.unverified:
        foot += " Competitor prices are unverified, so no price comparison is possible."
    text_box(
        slide,
        MARGIN_X + 0.2,
        y,
        hero_w - 0.4,
        top + avail - y - 0.1,
        Para(_short(foot, 230), 13, MUTED, align=PP_ALIGN.CENTER, after=0),
        pad=0.04,
        name="Price caveat",
    )

    rx = MARGIN_X + hero_w + GAP
    rw = CONTENT_W - hero_w - GAP
    pos_h = avail * 0.44
    ti = panel(slide, rx, top, rw, pos_h, "Proposed positioning", accent=PURPLE, reserve=2.0)
    chip(
        slide,
        rx + rw - chip_width("RECOMMENDATION", 11) - 0.15,
        top + 0.1,
        "RECOMMENDATION",
        PURPLE_DARK,
        PURPLE,
        size=11,
        line=PURPLE,
        name="Positioning tag",
    )
    pos = [
        Para(
            _short(_unlabel(s.positioning_line), 140) or "No positioning statement recorded.",
            22,
            TEXT,
            bold=True,
            after=8,
        )
    ]
    if s.recommended_offer:
        pos.append(Para(_short(_unlabel(s.recommended_offer), 320), 15, MUTED, after=0))
    text_box(
        slide,
        rx + 0.18,
        ti,
        rw - 0.3,
        top + pos_h - ti - 0.08,
        pos,
        pad=0.03,
        name="Positioning statement",
    )
    y2 = top + pos_h + GAP
    h2 = top + avail - y2
    half = (rw - GAP) / 2
    assumptions = ["The price point is untested with target customers."]
    if ctx.unverified:
        assumptions.append(
            "Competitor prices are unverified, so any premium or discount is unknown."
        )
    if s.rationale:
        assumptions.append(_short(s.rationale, 130))
    needs = [
        _short(b, 120)
        for b in spec.bullets
        if not _AMOUNT.search(b) and not b.lower().startswith("recommend")
    ][:3] or ["Specify serving size and delivery terms before sale."]
    for i, (heading, accent, lines) in enumerate(
        (("Key assumptions", BLUE, assumptions), ("Commercial validation needs", TEAL, needs))
    ):
        x = rx + i * (half + GAP)
        ti = panel(slide, x, y2, half, h2, heading, accent=accent)
        text_box(
            slide,
            x + 0.18,
            ti,
            half - 0.3,
            y2 + h2 - ti - 0.08,
            [Para(line, 15, TEXT, bullet=True, after=7) for line in lines],
            pad=0.03,
            name=f"Card {heading}",
        )
    price_note = f"Recommended price (full text): {s.recommended_price}"
    _notes(slide, spec, [price_note, *assumptions, *needs])


# ----------------------------------------------------------------------------- slide 6
def parse_weeks(bullets: list[str]) -> list[tuple[str, str]]:
    weeks = []
    for b in bullets:
        m = _WEEK.match(b)
        if m:
            weeks.append((f"Week {int(m.group(1))}", m.group(2).strip()))
    if weeks:
        return weeks
    return [(f"Step {i}", b) for i, b in enumerate(bullets, 1)]


def _slide_roadmap(prs, ctx: Ctx, index: int, spec: SlideSpec) -> None:
    slide, top = _chrome(prs, ctx, index, spec)
    weeks = parse_weeks(spec.bullets)[:4]
    if not weeks:
        text_box(
            slide,
            MARGIN_X,
            top + 0.3,
            CONTENT_W,
            1.0,
            Para("No launch plan actions were recorded.", 18, MUTED),
            fill=SURFACE,
            line=BORDER,
            name="No plan",
        )
        _notes(slide, spec, [])
        return
    n = len(weeks)
    ws = split_widths(CONTENT_W, n)
    text_box(
        slide,
        MARGIN_X,
        top,
        CONTENT_W,
        0.38,
        Para(
            "PROPOSED FUTURE ACTIONS — NOT COMPLETED OR VERIFIED",
            13,
            AMBER,
            bold=True,
            align=PP_ALIGN.CENTER,
            after=0,
        ),
        fill=AMBER_DARK,
        line=AMBER,
        anchor=MSO_ANCHOR.MIDDLE,
        pad=0.1,
        name="Plan status",
    )
    line_y = top + 0.38 + GAP + 0.32
    centers: list[float] = []
    x = MARGIN_X
    for w in ws:
        centers.append(x + w / 2)
        x += w + GAP
    for i in range(n - 1):
        arrow(
            slide,
            centers[i] + 0.35,
            line_y,
            centers[i + 1] - 0.35,
            line_y,
            TEAL,
            width_pt=3.0,
            name=f"Timeline link {i + 1}",
        )
    for c, (label, _) in zip(centers, weeks, strict=True):
        glyph = label.replace("Week ", "W").replace("Step ", "S")
        badge(
            slide, c - 0.3, line_y - 0.3, 0.6, glyph, TEAL, NAVY, size=15, name=f"Milestone {label}"
        )
    cards_top = line_y + 0.45
    card_h = CONTENT_BOTTOM - cards_top
    x = MARGIN_X
    detail: list[str] = []
    for (label, body), w in zip(weeks, ws, strict=True):
        clauses = [c.strip(" .") for c in re.split(r";\s*", body) if c.strip(" .")]
        heading = clauses[0] if len(clauses) > 1 else _short(body, 70)
        items = clauses[1:] if len(clauses) > 1 else [body.strip(" .")]
        detail.append(f"{label}: {body}")
        ti = panel(
            slide,
            x,
            cards_top,
            w,
            card_h,
            label,
            accent=TEAL,
            reserve=chip_width("PROPOSED", 10) + 0.2,
        )
        chip(
            slide,
            x + w - chip_width("PROPOSED", 10) - 0.12,
            cards_top + 0.08,
            "PROPOSED",
            AMBER_DARK,
            AMBER,
            size=10,
            h=0.31,
            line=AMBER,
            name=f"{label} tag",
        )
        hh = min(1.5, max(0.6, needed_height_in([Para(heading, 17, TEXT, bold=True)], w - 0.3)))
        text_box(
            slide,
            x + 0.18,
            ti,
            w - 0.3,
            hh,
            Para(heading, 17, TEXT, bold=True, after=0),
            pad=0.03,
            name=f"{label} focus",
        )
        text_box(
            slide,
            x + 0.18,
            ti + hh + 0.02,
            w - 0.3,
            cards_top + card_h - (ti + hh) - 0.1,
            [
                Para("PLANNED OUTPUTS", 11, MUTED, bold=True, after=4),
                *[Para(i, 15, TEXT, bullet=True, after=7) for i in items],
            ],
            pad=0.03,
            name=f"{label} actions",
        )
        x += w + GAP
    _notes(slide, spec, detail)


# ----------------------------------------------------------------------------- entry points
_LAYOUTS = (
    _slide_dashboard,
    _slide_matrix,
    _slide_evidence,
    _slide_flow,
    _slide_pricing,
    _slide_roadmap,
)


def build_pptx(deck: DeckSpec, source: DeckSource, path: Path, generated_on: date) -> Path:
    """Write the deck: exactly six slides, native editable shapes, LS logo on every slide."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(int(Inches(SLIDE_W))), Emu(int(Inches(SLIDE_H)))
    ctx = Ctx(deck, source, generated_on)
    for index, (layout, slide_spec) in enumerate(zip(_LAYOUTS, deck.slides, strict=True), 1):
        layout(prs, ctx, index, slide_spec)
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
        ppr = para._p.pPr
        bulleted = ppr is not None and ppr.find(f"{_A_NS}buChar") is not None
        content = "".join(r.text for r in para.runs)
        lines = estimate_lines(content, width_pt - (16 if bulleted else 0), size)
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
    band_top, band_bottom = 1.3, FOOTER_TOP
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
