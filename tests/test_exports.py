"""Markdown/PDF exports and link checking: deterministic, no model, no real network."""

from datetime import date

import pdfplumber

from launchscout.evidence import EvidenceEntry, EvidenceLedger
from launchscout.exports.markdown import write_report_files
from launchscout.exports.pdf import markdown_to_pdf
from launchscout.links import check_links, classify
from tests.helpers import MENU_URLS, PASS_REPORT_MD


def test_pdf_contains_sections_table_links_and_rupee(tmp_path):
    out = tmp_path / "r.pdf"
    pages = markdown_to_pdf(PASS_REPORT_MD, out, title="Test run")
    assert pages >= 1 and out.stat().st_size > 1000
    with pdfplumber.open(out) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        links = [h["uri"] for p in pdf.pages for h in p.hyperlinks]
    for heading in (
        "Key Competitors",
        "What Customers Complain About",
        "Market Gap",
        "Recommended Positioning",
        "30-Day Launch Plan",
        "Sources",
    ):
        assert heading in text
    assert "Millet Kitchen" in text and "180" in text
    assert any(u.startswith("https://millet-kitchen.example") for u in links)
    assert "Week 1" in text


def test_pdf_handles_hostile_markup_without_breaking(tmp_path):
    md = "## Title\n<script>alert(1)</script> & <b>x</b> [bad](https://a.example/?q=1&r=2)\n"
    out = tmp_path / "h.pdf"
    markdown_to_pdf(md, out)
    with pdfplumber.open(out) as pdf:
        text = pdf.pages[0].extract_text()
    assert "<script>" in text  # shown literally, not interpreted


def test_partial_report_never_written_as_validated_name(tmp_path):
    write_report_files(tmp_path, "# ok", "validated_pass", "t")
    assert (tmp_path / "report.md").exists() and (tmp_path / "report.pdf").exists()
    write_report_files(tmp_path, "# partial", "partial_failed_acceptance", "t")
    assert not (tmp_path / "report.md").exists() and not (tmp_path / "report.pdf").exists()
    assert (tmp_path / "report-PARTIAL.md").read_text(encoding="utf-8") == "# partial"
    assert (tmp_path / "report-PARTIAL.pdf").exists()
    write_report_files(tmp_path, "# ok again", "validated_pass", "t")
    assert not (tmp_path / "report-PARTIAL.md").exists()


def _ledger_with_scraped(url: str) -> EvidenceLedger:
    led = EvidenceLedger()
    led.add(EvidenceEntry(url=url, kind="scraped", accessed_on=date(2026, 10, 14)))
    return led


def test_pages_read_during_research_are_not_requested_again():
    calls: list[str] = []

    def fetcher(url: str, timeout: float) -> int:
        calls.append(url)
        return 200

    led = _ledger_with_scraped(MENU_URLS[0])
    result = check_links([MENU_URLS[0], MENU_URLS[1]], led, fetcher)
    assert calls == [MENU_URLS[1]]
    assert result[0].status == "ok" and result[0].source == "research"
    assert result[1].source == "checked"


def test_link_status_classification_and_bounds():
    assert classify(200) == "ok" and classify(301) == "ok"
    assert classify(403) == "blocked" and classify(429) == "blocked"
    assert classify(404) == "broken" and classify(503) == "broken"

    def flaky(url: str, timeout: float) -> int:
        if "boom" in url:
            raise TimeoutError("slow")
        return 404 if "gone" in url else 200

    urls = [f"https://ok{i}.example/" for i in range(5)] + [
        "https://gone.example/",
        "https://boom.example/",
    ]
    result = check_links(urls, EvidenceLedger(), flaky, max_checks=7)
    by = {r.url: r for r in result}
    assert by["https://gone.example/"].status == "broken"
    assert by["https://boom.example/"].status == "broken"
    assert by["https://ok0.example/"].status == "ok"
    limited = check_links(urls, EvidenceLedger(), flaky, max_checks=6)
    assert sum(1 for r in limited if r.status == "not_checked") == 1  # limit respected


def test_live_link_checks_disabled_in_tests():
    result = check_links(["https://a.example/"], EvidenceLedger())
    assert result[0].status == "not_checked" and result[0].source == "skipped"
