"""Write the validated (or clearly partial) report files for a run, Markdown and PDF."""

from __future__ import annotations

from pathlib import Path

from launchscout.exports.pdf import markdown_to_pdf
from launchscout.report import report_filenames

ALL_REPORT_FILES = ("report.md", "report.pdf", "report-PARTIAL.md", "report-PARTIAL.pdf")


def write_report_files(root: Path, final_markdown: str, state: str, title: str) -> dict[str, str]:
    """Write the report pair for `state`, removing the other variant.

    A partial report is never written as `report.md`/`report.pdf`; a passing report never
    keeps stale `-PARTIAL` files. Returns {"md": name, "pdf": name}.
    """
    md_name, pdf_name = report_filenames(state)
    for name in ALL_REPORT_FILES:
        if name not in (md_name, pdf_name):
            stale = root / name
            if stale.exists():
                stale.unlink()
    (root / md_name).write_text(final_markdown, encoding="utf-8")
    markdown_to_pdf(final_markdown, root / pdf_name, title=title)
    return {"md": md_name, "pdf": pdf_name}
