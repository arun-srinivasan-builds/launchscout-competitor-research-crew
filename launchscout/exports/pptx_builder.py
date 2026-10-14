"""Render a `DeckSpec` as a native, editable PowerPoint (text boxes, no images).

Visual language follows the app: dark navy background, teal accent, soft text, amber labels.
Every slide is plain shapes and text so the user can edit everything in PowerPoint.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from launchscout.schemas import DeckSpec, SlideSpec

if TYPE_CHECKING:
    from launchscout.deck import DeckSource

NAVY = RGBColor(0x05, 0x0C, 0x1C)
SURFACE = RGBColor(0x0C, 0x18, 0x30)
TEAL = RGBColor(0x2D, 0xD4, 0xBF)
TEXT = RGBColor(0xE8, 0xEE, 0xF8)
MUTED = RGBColor(0x9F, 0xB2, 0xCC)
AMBER = RGBColor(0xFB, 0xBF, 0x24)
LABEL_FILL = RGBColor(0x2A, 0x22, 0x08)
FONT = "Calibri"
WIDTH, HEIGHT = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.7)
GLYPH_EM = 0.55  # conservative average glyph width (bold Calibri) as a fraction of the size
LINE_SPACING = 1.2
BANNER_PAD_PT = 7.0


def estimate_lines(text: str, width_pt: float, size_pt: float) -> int:
    """Wrapped line count estimate shared by the layout and the bounds check."""
    per_line = max(1, int(width_pt / (size_pt * GLYPH_EM)))
    return max(1, -(-len(text) // per_line))


def _text_box(slide, left, top, width, height, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = Inches(0.05)
    return box, frame


def _style(run, size: int, color: RGBColor, bold: bool = False) -> None:
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _bullet(paragraph) -> None:
    """Real PowerPoint bullet (a:buChar), so the list stays a native, editable list."""
    props = paragraph._p.get_or_add_pPr()
    props.set("marL", str(int(Inches(0.3))))
    props.set("indent", str(-int(Inches(0.3))))
    for tag in ("a:buNone", "a:buChar"):
        for child in props.findall(qn(tag)):
            props.remove(child)
    char = props.makeelement(qn("a:buChar"), {"char": "•"})
    props.append(char)


def _slide(prs: Presentation, spec: SlideSpec, index: int, footer: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = NAVY

    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, MARGIN, Inches(0.55), Inches(0.12), Inches(0.75)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = TEAL
    bar.line.fill.background()
    bar.name = "Accent bar"

    title_box, tf = _text_box(
        slide,
        MARGIN + Inches(0.3),
        Inches(0.45),
        WIDTH - 2 * MARGIN,
        Inches(0.95),
        MSO_ANCHOR.MIDDLE,
    )
    title_box.name = "Title"
    run = tf.paragraphs[0].add_run()
    run.text = spec.title
    _style(run, 34, TEXT, bold=True)

    top = Inches(1.55)
    if spec.labels:
        banner_w = WIDTH - 2 * MARGIN
        label_pt = 12
        lines = sum(
            estimate_lines(label, banner_w / 12700 - 2 * BANNER_PAD_PT, label_pt)
            for label in spec.labels
        )
        banner_h = Pt(lines * label_pt * LINE_SPACING + 2 * BANNER_PAD_PT)
        label_box, lf = _text_box(slide, MARGIN, top, banner_w, banner_h, MSO_ANCHOR.MIDDLE)
        label_box.name = "Labels"
        label_box.fill.solid()
        label_box.fill.fore_color.rgb = LABEL_FILL
        lf.margin_left = lf.margin_right = Pt(BANNER_PAD_PT)
        lf.margin_top = lf.margin_bottom = Pt(BANNER_PAD_PT)
        for i, label in enumerate(spec.labels):
            para = lf.paragraphs[0] if i == 0 else lf.add_paragraph()
            r = para.add_run()
            r.text = label
            _style(r, label_pt, AMBER, bold=True)
        top += banner_h + Inches(0.2)

    body_box, bf = _text_box(slide, MARGIN, top, WIDTH - 2 * MARGIN, HEIGHT - top - Inches(1.0))
    body_box.name = "Body"
    for i, text in enumerate(spec.bullets):
        para = bf.paragraphs[0] if i == 0 else bf.add_paragraph()
        para.space_after = Pt(10)
        _bullet(para)
        r = para.add_run()
        r.text = text
        _style(r, 20, TEXT)
    if not spec.bullets:
        r = bf.paragraphs[0].add_run()
        r.text = "No evidenced content for this slide."
        _style(r, 20, MUTED)

    # two lines of 11pt fit: the footer string (idea, run id, date) can wrap on long ideas
    foot_box, ff = _text_box(
        slide, MARGIN, HEIGHT - Inches(0.7), WIDTH - 2 * MARGIN - Inches(1.2), Inches(0.55)
    )
    foot_box.name = "Footer"
    fr = ff.paragraphs[0].add_run()
    fr.text = footer
    _style(fr, 11, MUTED)
    num_box, nf = _text_box(
        slide, WIDTH - MARGIN - Inches(1.2), HEIGHT - Inches(0.7), Inches(1.2), Inches(0.4)
    )
    num_box.name = "Slide number"
    nf.paragraphs[0].alignment = PP_ALIGN.RIGHT
    nr = nf.paragraphs[0].add_run()
    nr.text = f"{index} / 6"
    _style(nr, 11, TEAL, bold=True)

    notes = [spec.notes.strip()] if spec.notes.strip() else []
    if spec.source_refs:
        notes.append("Sources:\n" + "\n".join(spec.source_refs))
    if spec.labels:
        notes.append("Labels: " + "; ".join(spec.labels))
    slide.notes_slide.notes_text_frame.text = "\n\n".join(notes)


def build_pptx(deck: DeckSpec, source: DeckSource, path: Path, generated_on: date) -> Path:
    """Write the deck. Exactly six slides, all native text shapes."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(int(WIDTH)), Emu(int(HEIGHT))
    state = "PARTIAL evidence" if source.partial else "validated report"
    footer = (
        f"LaunchScout · {source.input.idea} · {source.input.city} · {state} · "
        f"run {source.run_id} · generated {generated_on.isoformat()}"
    )
    for index, slide in enumerate(deck.slides, 1):
        _slide(prs, slide, index, footer)
    prs.core_properties.title = f"LaunchScout pitch deck: {source.input.idea}"
    prs.core_properties.author = "LaunchScout"
    path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(path))
    return path


def check_text_bounds(path: Path) -> list[str]:
    """Programmatic text-fit estimate (not a render).

    Flags text likely to overflow its box (including wrapped label banners), run past the
    footer, overlap the body, or leave the slide.
    """
    prs = Presentation(str(path))
    problems: list[str] = []
    footer_top = int(HEIGHT - Inches(0.7))
    for number, slide in enumerate(prs.slides, 1):
        body = next((x for x in slide.shapes if x.name == "Body"), None)
        for shape in slide.shapes:
            if not shape.has_text_frame or not shape.text_frame.text.strip():
                continue
            if shape.left < 0 or shape.top < 0 or shape.left + shape.width > prs.slide_width:
                problems.append(f"slide {number}: '{shape.name}' extends outside the slide")
            frame = shape.text_frame
            pad = (frame.margin_left + frame.margin_right) / 12700
            width_pt = shape.width / 12700 - pad
            total_pt = 0.0
            for para in frame.paragraphs:
                size = max((r.font.size.pt for r in para.runs if r.font.size), default=18.0)
                indent = 22.0 if shape.name == "Body" else 0.0
                text = "".join(r.text for r in para.runs)
                lines = estimate_lines(text, width_pt - indent, size)
                total_pt += lines * size * LINE_SPACING + (10 if shape.name == "Body" else 0)
            vpad = (frame.margin_top + frame.margin_bottom) / 12700
            needed = int((total_pt + vpad) * 12700)
            if shape.name == "Labels":
                if needed > shape.height:
                    problems.append(f"slide {number}: label text may wrap outside its banner")
                if body is not None and shape.top + shape.height > body.top:
                    problems.append(f"slide {number}: label banner overlaps the body text")
                if shape.top + shape.height > footer_top:
                    problems.append(f"slide {number}: label banner runs into the footer")
            elif shape.name == "Body":
                if shape.top + needed > footer_top:
                    problems.append(f"slide {number}: 'Body' text may run into the footer")
            elif shape.name in ("Title", "Footer") and needed > shape.height:
                problems.append(f"slide {number}: '{shape.name}' text may wrap beyond its box")
    return problems
