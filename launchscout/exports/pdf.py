"""Markdown -> PDF with reportlab. Deterministic; no model, no network."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_FONT_CANDIDATES: tuple[tuple[str, str], ...] = (
    (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
)
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_TAGS = {"unverified link", "unverified price"}


def _register_fonts() -> tuple[str, str, bool]:
    """(regular, bold, unicode_ok). Falls back to Helvetica with ASCII-safe text."""
    for regular, bold in _FONT_CANDIDATES:
        if Path(regular).is_file() and Path(bold).is_file():
            try:
                pdfmetrics.registerFont(TTFont("LS-Regular", regular))
                pdfmetrics.registerFont(TTFont("LS-Bold", bold))
                return "LS-Regular", "LS-Bold", True
            except Exception:  # noqa: BLE001 - try the next candidate
                continue
    return "Helvetica", "Helvetica-Bold", False


def _safe(text: str, unicode_ok: bool) -> str:
    if unicode_ok:
        return text
    text = text.replace("₹", "Rs ").replace("€", "EUR ")
    return text.encode("latin-1", "replace").decode("latin-1")


def _inline(text: str, unicode_ok: bool) -> str:
    """Markdown inline -> reportlab mini-HTML. Links stay clickable; text is escaped."""
    text = _safe(text, unicode_ok)
    parts: list[str] = []
    placeholders: dict[str, str] = {}

    def stash(markup: str) -> str:
        key = f"\u0000{len(placeholders)}\u0000"
        placeholders[key] = markup
        return key

    def link_sub(match: re.Match[str]) -> str:
        label, url = match.group(1), match.group(2)
        return stash(
            f'<a href="{html.escape(url, quote=True)}" color="#1d4ed8">{html.escape(label)}</a>'
        )

    text = _LINK_RE.sub(link_sub, text)

    def url_sub(match: re.Match[str]) -> str:
        url = match.group(0).rstrip(".,;:")
        tail = match.group(0)[len(url):]
        link = f'<a href="{html.escape(url, quote=True)}" color="#1d4ed8">{html.escape(url)}</a>'
        return stash(link) + html.escape(tail)

    # bare URLs outside placeholders
    pieces = re.split("(\u0000\\d+\u0000)", text)
    for piece in pieces:
        if piece.startswith("\u0000"):
            parts.append(piece)
        else:
            parts.append(_URL_RE.sub(url_sub, piece))
    text = "".join(parts)
    # escape everything that is not a placeholder, then re-apply bold/code
    chunks = re.split("(\u0000\\d+\u0000)", text)
    escaped = "".join(c if c.startswith("\u0000") else html.escape(c, quote=False) for c in chunks)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', escaped)
    for key, markup in placeholders.items():
        escaped = escaped.replace(html.escape(key, quote=False), markup).replace(key, markup)
    return escaped


def markdown_to_pdf(markdown: str, path: Path, title: str = "LaunchScout report") -> int:
    """Write `markdown` as a PDF at `path`. Returns the page count."""
    regular, bold, unicode_ok = _register_fonts()
    styles = getSampleStyleSheet()
    body = ParagraphStyle("LSBody", parent=styles["BodyText"], fontName=regular, fontSize=10,
                          leading=14, alignment=TA_LEFT, spaceAfter=6)
    h1 = ParagraphStyle("LSH1", parent=body, fontName=bold, fontSize=18, leading=22, spaceAfter=10,
                        textColor=colors.HexColor("#0B2545"))
    h2 = ParagraphStyle("LSH2", parent=body, fontName=bold, fontSize=14, leading=18, spaceBefore=10,
                        spaceAfter=6, textColor=colors.HexColor("#13315C"))
    h3 = ParagraphStyle("LSH3", parent=body, fontName=bold, fontSize=11.5, leading=15,
                        spaceBefore=8, spaceAfter=4)
    quote = ParagraphStyle(
        "LSQuote", parent=body, leftIndent=8, borderPadding=6, borderWidth=0.8,
        backColor=colors.HexColor("#FFF7E6"), borderColor=colors.HexColor("#8A5A00"),
    )
    cell = ParagraphStyle("LSCell", parent=body, fontSize=8.5, leading=11, spaceAfter=0)
    cell_head = ParagraphStyle("LSCellHead", parent=cell, fontName=bold)

    flow: list = []
    lines = markdown.splitlines()
    i = 0
    para: list[str] = []

    def flush_para() -> None:
        if para:
            flow.append(Paragraph(_inline(" ".join(para), unicode_ok), body))
            para.clear()

    width = A4[0] - 30 * mm
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush_para()
            i += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_para()
            level = len(heading.group(1))
            style = h1 if level == 1 else h2 if level == 2 else h3
            flow.append(Paragraph(_inline(heading.group(2), unicode_ok), style))
            i += 1
            continue
        if stripped.startswith("|"):
            flush_para()
            block: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) or not c for c in cells):
                    block.append(cells)
                i += 1
            if block:
                cols = max(len(r) for r in block)
                data = [
                    [Paragraph(_inline(c, unicode_ok), cell_head if r == 0 else cell)
                     for c in row + [""] * (cols - len(row))]
                    for r, row in enumerate(block)
                ]
                table = Table(data, colWidths=[width / cols] * cols, repeatRows=1)
                table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9FB2CC")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4ECF4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                flow += [table, Spacer(1, 6)]
            continue
        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
            flush_para()
            items: list[ListItem] = []
            ordered = bool(re.match(r"^\d+[.)]\s+", stripped))
            item_re = re.compile(r"^([-*]|\d+[.)])\s+")
            while i < len(lines) and item_re.match(lines[i].strip()):
                text = re.sub(r"^([-*]|\d+[.)])\s+", "", lines[i].strip())
                items.append(ListItem(Paragraph(_inline(text, unicode_ok), body)))
                i += 1
            flow.append(ListFlowable(items, bulletType="1" if ordered else "bullet",
                                     leftIndent=14))
            continue
        if stripped.startswith(">"):
            flush_para()
            quoted: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quoted.append(lines[i].strip().lstrip(">").strip())
                i += 1
            marked = ["• " + q[2:] if q.startswith("- ") else q for q in quoted if q]
            flow.append(
                Paragraph("<br/>".join(_inline(q, unicode_ok) for q in marked), quote)
            )
            continue
        para.append(stripped)
        i += 1
    flush_para()

    pages = {"n": 0}

    def footer(canvas, doc) -> None:  # noqa: ANN001 - reportlab callback signature
        canvas.saveState()
        canvas.setFont(regular, 8)
        canvas.setFillColor(colors.HexColor("#4A5D73"))
        canvas.drawString(15 * mm, 10 * mm, f"LaunchScout - {_safe(title, unicode_ok)[:80]}")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()
        pages["n"] = doc.page

    doc = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm,
        bottomMargin=18 * mm, title=_safe(title, unicode_ok), author="LaunchScout",
    )
    doc.build(flow or [Paragraph("(empty report)", body)], onFirstPage=footer, onLaterPages=footer)
    return pages["n"]
