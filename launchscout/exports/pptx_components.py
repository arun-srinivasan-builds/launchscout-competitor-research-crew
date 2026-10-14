"""Reusable, content-agnostic PowerPoint building blocks (python-pptx, all native shapes).

Nothing here knows about a particular business idea. Layout functions in `pptx_builder` compose
these into slides. Every text element is fitted to its box: the font shrinks to a floor and
then the text is shortened with an ellipsis (the full text always goes to the speaker notes).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

# ---- palette (matches the app theme) ---------------------------------------------------------
NAVY = RGBColor(0x05, 0x0C, 0x1C)
SURFACE = RGBColor(0x0C, 0x18, 0x30)
SURFACE_2 = RGBColor(0x11, 0x22, 0x44)
BORDER = RGBColor(0x27, 0x40, 0x6B)
TEXT = RGBColor(0xE8, 0xEE, 0xF8)
MUTED = RGBColor(0x9F, 0xB2, 0xCC)
TEAL = RGBColor(0x2D, 0xD4, 0xBF)
TEAL_DARK = RGBColor(0x0F, 0x3B, 0x3B)
AMBER = RGBColor(0xFB, 0xBF, 0x24)
AMBER_DARK = RGBColor(0x2A, 0x22, 0x08)
BLUE = RGBColor(0x38, 0xBD, 0xF8)
PURPLE = RGBColor(0x8B, 0x5C, 0xF6)
PURPLE_DARK = RGBColor(0x1E, 0x16, 0x3D)
RED = RGBColor(0xF8, 0x71, 0x71)
SOFT_WHITE = RGBColor(0xF7, 0xF9, 0xFB)
FONT = "Calibri"

# ---- geometry (inches) -----------------------------------------------------------------------
SLIDE_W, SLIDE_H = 13.333, 7.5
MARGIN_X = 0.5
CONTENT_W = SLIDE_W - 2 * MARGIN_X
FOOTER_TOP = 6.95
CONTENT_BOTTOM = 6.8
GAP = 0.18

GLYPH_EM = 0.5  # average Calibri glyph width (incl. capitals and bold) as a fraction of the size
LINE_SPACING = 1.2
MIN_SIZE = 11


def estimate_lines(text: str, width_pt: float, size_pt: float) -> int:
    """Wrapped line count estimate (word-aware) shared by layout and the bounds check."""
    per_line = max(1, int(width_pt / (size_pt * GLYPH_EM)))
    lines = 0
    for raw in text.split("\n") or [""]:
        count, current = 1, 0
        for word in raw.split(" "):
            need = len(word) + (1 if current else 0)
            if current + need <= per_line:
                current += need
            else:
                count += 1 if current else 0
                current = len(word)
                while current > per_line:  # an over-long token wraps by character
                    count += 1
                    current -= per_line
        lines += count
    return max(1, lines)


@dataclass
class Para:
    text: str
    size: float = 13
    color: RGBColor = TEXT
    bold: bool = False
    bullet: bool = False
    after: float = 4  # points of space after
    align: PP_ALIGN = PP_ALIGN.LEFT
    italic: bool = False


@dataclass
class Fit:
    paras: list[Para] = field(default_factory=list)
    truncated: bool = False


BULLET_INDENT_PT = 16.0


def _needed_pt(paras: Sequence[Para], width_pt: float) -> float:
    total = 0.0
    for p in paras:
        indent = BULLET_INDENT_PT if p.bullet else 0.0
        lines = estimate_lines(p.text, width_pt - indent, p.size)
        total += lines * p.size * LINE_SPACING + p.after
    return total


def _shorten(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[: max(1, max_chars - 1)].rsplit(" ", 1)[0].rstrip(",;:.- ")
    return (cut or text[: max_chars - 1]) + "…"


def fit_paragraphs(paras: Sequence[Para], width_pt: float, height_pt: float) -> Fit:
    """Shrink fonts (down to MIN_SIZE) then shorten text until the paragraphs fit the box."""
    work = [Para(**p.__dict__) for p in paras]
    while _needed_pt(work, width_pt) > height_pt and any(p.size > MIN_SIZE for p in work):
        for p in work:  # shrink every paragraph one point, never below the readability floor
            p.size = max(MIN_SIZE, p.size - 1)
    truncated = False
    guard = 0
    while _needed_pt(work, width_pt) > height_pt and guard < 200:
        guard += 1
        longest = max(work, key=lambda p: len(p.text), default=None)
        if longest is None or len(longest.text) <= 12:
            break
        longest.text = _shorten(longest.text, int(len(longest.text) * 0.85))
        truncated = True
    return Fit(work, truncated)


def _apply_run(run, p: Para) -> None:
    run.font.name = FONT
    run.font.size = Pt(p.size)
    run.font.bold = p.bold
    run.font.italic = p.italic
    run.font.color.rgb = p.color


def _set_bullet(paragraph) -> None:
    props = paragraph._p.get_or_add_pPr()
    props.set("marL", str(int(Pt(BULLET_INDENT_PT))))
    props.set("indent", str(-int(Pt(BULLET_INDENT_PT))))
    for tag in ("a:buNone", "a:buChar"):
        for child in props.findall(qn(tag)):
            props.remove(child)
    props.append(props.makeelement(qn("a:buChar"), {"char": "•"}))


def box(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: RGBColor | None = None,
    line: RGBColor | None = None,
    line_w: float = 1.0,
    round_: bool = True,
    shape: MSO_SHAPE | None = None,
    name: str | None = None,
):
    """A filled rectangle / rounded rectangle / other autoshape without text."""
    kind = shape or (MSO_SHAPE.ROUNDED_RECTANGLE if round_ else MSO_SHAPE.RECTANGLE)
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = min(0.5, 0.08 / max(min(w, h), 0.2))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(line_w)
    s.shadow.inherit = False
    if name:
        s.name = name
    return s


def text(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    paras: Sequence[Para] | Para,
    *,
    fill: RGBColor | None = None,
    line: RGBColor | None = None,
    anchor: MSO_ANCHOR = MSO_ANCHOR.TOP,
    pad: float = 0.08,
    round_: bool = True,
    shape: MSO_SHAPE | None = None,
    name: str | None = None,
    line_w: float = 1.0,
    wrap: bool = True,
):
    """A text-bearing shape whose text is fitted to the box. Returns (shape, Fit)."""
    items = [paras] if isinstance(paras, Para) else list(paras)
    if fill is None and line is None and shape is None:
        s = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    else:
        s = box(slide, x, y, w, h, fill=fill, line=line, round_=round_, shape=shape, line_w=line_w)
    frame = s.text_frame
    frame.word_wrap = wrap
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = Inches(pad)
    frame.margin_top = frame.margin_bottom = Inches(min(pad, 0.06))
    width_pt = (w - 2 * pad) * 72
    height_pt = (h - 2 * min(pad, 0.06)) * 72
    fit = fit_paragraphs(items, width_pt, height_pt)
    for i, p in enumerate(fit.paras):
        para = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        para.alignment = p.align
        para.space_after = Pt(p.after)
        if p.bullet:
            _set_bullet(para)
        run = para.add_run()
        run.text = p.text
        _apply_run(run, p)
    if name:
        s.name = name
    return s, fit


def needed_height_in(paras: Sequence[Para], w: float, pad: float = 0.08) -> float:
    """Height (inches) a text box of width `w` needs for these paragraphs."""
    return (_needed_pt(paras, (w - 2 * pad) * 72) / 72) + 2 * min(pad, 0.06) + 0.02


CAPS_EM = 0.65  # bold capitals are wider than average text; LibreOffice also renders wider


def chip_width(label: str, size: float = 11, pad: float = 0.16) -> float:
    """Width that holds the whole label on one line, with padding either side."""
    return len(label) * size * CAPS_EM / 72 + 2 * pad + 0.12


def chip(
    slide,
    x: float,
    y: float,
    label: str,
    fill: RGBColor,
    color: RGBColor,
    *,
    size: float = 11,
    h: float = 0.32,
    name: str | None = None,
    line: RGBColor | None = None,
):
    """A pill-shaped status chip. Returns (shape, width)."""
    w = chip_width(label, size)
    s, _ = text(
        slide,
        x,
        y,
        w,
        h,
        Para(label, size, color, bold=True, align=PP_ALIGN.CENTER, after=0),
        fill=fill,
        line=line,
        anchor=MSO_ANCHOR.MIDDLE,
        pad=0.16,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        name=name,
        wrap=False,  # a status label must never break onto a second line
    )
    s.adjustments[0] = 0.5
    return s, w


def badge(
    slide,
    x: float,
    y: float,
    d: float,
    glyph: str,
    fill: RGBColor,
    color: RGBColor = NAVY,
    *,
    size: float = 12,
    name: str | None = None,
):
    """A round icon badge with a short glyph."""
    s, _ = text(
        slide,
        x,
        y,
        d,
        d,
        Para(glyph, size, color, bold=True, align=PP_ALIGN.CENTER, after=0),
        fill=fill,
        anchor=MSO_ANCHOR.MIDDLE,
        pad=0.0,
        wrap=False,
        shape=MSO_SHAPE.OVAL,
        name=name,
    )
    return s


def arrow(
    slide,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: RGBColor = TEAL,
    *,
    width_pt: float = 2.25,
    head: bool = True,
    name: str | None = None,
):
    """A native connector with an optional arrowhead."""
    c = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    c.line.color.rgb = color
    c.line.width = Pt(width_pt)
    if head:
        ln = c.line._get_or_add_ln()
        tail = etree.SubElement(ln, qn("a:tailEnd"))
        tail.set("type", "triangle")
        tail.set("w", "med")
        tail.set("len", "med")
    if name:
        c.name = name
    return c


def panel(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    heading: str | None = None,
    *,
    accent: RGBColor = TEAL,
    fill: RGBColor = SURFACE,
    name: str | None = None,
    reserve: float = 0.0,
) -> float:
    """A bordered card with an accent strip and optional heading. Returns the inner top y."""
    box(slide, x, y, w, h, fill=fill, line=BORDER, name=name)
    box(slide, x, y + 0.1, 0.07, h - 0.2, fill=accent, round_=False, name="Accent")
    inner = y + 0.1
    if heading:
        text(
            slide,
            x + 0.18,
            y + 0.08,
            w - 0.3 - reserve,
            0.34,
            Para(heading.upper(), 12, accent, bold=True, after=0),
            pad=0.02,
            name="Panel heading",
        )
        inner = y + 0.46
    return inner


def kpi_tile(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    value: str,
    label: str,
    caption: str,
    accent: RGBColor = TEAL,
) -> None:
    """Large KPI: big value, bold label, muted caption."""
    box(slide, x, y, w, h, fill=SURFACE, line=BORDER, name="KPI tile")
    box(slide, x, y, w, 0.07, fill=accent, round_=False, name="Accent")
    value_h = h * 0.34
    text(
        slide,
        x + 0.15,
        y + 0.15,
        w - 0.3,
        value_h,
        Para(value, 40 if len(value) <= 6 else 28, accent, bold=True, after=0),
        anchor=MSO_ANCHOR.MIDDLE,
        pad=0.02,
        name="KPI value",
    )
    text(
        slide,
        x + 0.15,
        y + 0.15 + value_h,
        w - 0.3,
        0.38,
        Para(label, 14, TEXT, bold=True, after=0),
        pad=0.02,
        name="KPI label",
    )
    rest = h - (0.15 + value_h + 0.38) - 0.1
    text(
        slide,
        x + 0.15,
        y + 0.15 + value_h + 0.38,
        w - 0.3,
        max(0.3, rest),
        Para(caption, 12, MUTED, after=0),
        pad=0.02,
        name="KPI caption",
    )


def split_widths(total: float, n: int, gap: float = GAP) -> list[float]:
    n = max(1, n)
    each = (total - gap * (n - 1)) / n
    return [each] * n
