"""Deterministic report assembly: in-place unverified tags, warning header, verification summary.

The Report Writer agent's text is never trusted as final. This module reads its output plus the
stored structured outputs and evidence, and produces the report that is shown and exported.
No model calls happen here.
"""

from __future__ import annotations

import re
from collections import Counter

from launchscout.evidence import EvidenceLedger
from launchscout.grounding import report_unsupported_urls
from launchscout.schemas import Competitor, CompetitorSet, ReviewSet, StrategyOutput
from launchscout.validation import (
    _ACK_RE,
    _AMOUNT_RE,
    ValidationReport,
    section_key,
    split_top_sections,
)

UNVERIFIED_LINK_TAG = "**[unverified link]**"
UNVERIFIED_PRICE_TAG = "**[unverified price]**"


def tag_unsupported_urls(markdown: str, unsupported: list[str]) -> str:
    """Tag, never delete, every URL no tool returned."""
    out = markdown
    for url in sorted(set(unsupported), key=len, reverse=True):
        esc = re.escape(url)
        md_link = rf"(\[[^\]]*\]\({esc}\))(?! \*\*\[unverified)"
        out = re.sub(md_link, rf"\1 {UNVERIFIED_LINK_TAG}", out)
        out = re.sub(
            rf"(?<!\]\()({esc})(?![\w/#?=&%-])(?! \*\*\[unverified)",
            rf"\1 {UNVERIFIED_LINK_TAG}",
            out,
        )
    return out


def _bad_price_competitor(line: str, competitors: list[Competitor]) -> Competitor | None:
    lowered = line.casefold()
    for comp in competitors:
        name = comp.name.casefold().strip()
        if not name or name not in lowered:
            continue
        found = [
            m
            for m in _AMOUNT_RE.finditer(line)
            if not _ACK_RE.search(line[max(0, m.start() - 70) : m.end() + 70])
        ]
        if not found:
            return None
        if comp.price.status != "verified":
            return comp
        values = []
        for match in found:
            raw = (match.group(1) or match.group(2) or "").replace(",", "")
            try:
                values.append(float(raw))
            except ValueError:
                continue
        if comp.price.amount is not None and not any(
            abs(v - comp.price.amount) < 0.005 for v in values
        ):
            return comp
        return None
    return None


def tag_unverified_prices(markdown: str, competitors: list[Competitor]) -> str:
    """Tag amounts in competitor-table rows that are not backed by a verified price."""
    out: list[str] = []
    for line in markdown.splitlines():
        if line.strip().startswith("|") and _bad_price_competitor(line, competitors):
            line = _AMOUNT_RE.sub(lambda m: f"{m.group(0)} {UNVERIFIED_PRICE_TAG}", line)
        out.append(line)
    return "\n".join(out)


def partial_header(validation: ValidationReport) -> str:
    reasons = "\n".join(f"> - {r}" for r in validation.acceptance.reasons) or "> - (none recorded)"
    return (
        "> **FAILED ACCEPTANCE - PARTIAL RESEARCH.** This report is not validated and must not "
        "be treated as final.\n>\n> Failed rules and reasons:\n"
        f"{reasons}\n>\n"
        "> Items tagged **[unverified link]** or **[unverified price]** are not supported by "
        "evidence the research tools returned. Unknown means not evidenced.\n"
    )


def pass_header(run_id: str) -> str:
    return (
        f"> **Acceptance passed.** All deterministic checks passed for run `{run_id}`. "
        "Recommendations are labelled and are not verified facts.\n"
    )


def _price_text(comp: Competitor) -> str:
    p = comp.price
    if p.status != "verified" or p.amount is None:
        return "unknown"
    pack = f", {p.pack_size}" if p.pack_size else ""
    return f"{p.amount:g} {p.currency} {p.unit}{pack}"


def verification_summary(
    validation: ValidationReport,
    competitors: CompetitorSet | None,
    reviews: ReviewSet | None,
    strategy: StrategyOutput | None,
    ledger: EvidenceLedger,
) -> str:
    """Generated subsection that labels verified, unknown, inferred and recommended content."""
    lines = [
        "### Verification status (generated from stored evidence; no model involved)",
        "",
        "**Verified facts** are limited to what a retrieved page states. "
        "**Unknown** means not evidenced. **Inferred** means no retrieved source. "
        "**Recommendation** is a proposal, not a fact.",
        "",
    ]
    comps = competitors.competitors if competitors else []
    if comps:
        # a list, not a table: evidence URLs are long and tables overflow narrow screens
        for c in comps:
            status = "verified" if c.price.status == "verified" else "unknown"
            lines.append(f"- **{c.name}** - price status: {status}; price: {_price_text(c)}")
            if c.evidence_urls:
                lines += [f"  - evidence: {u}" for u in c.evidence_urls]
            else:
                lines.append("  - evidence: none returned by tools")
        lines.append("")
        unknowns = [(c.name, u) for c in comps for u in c.unknowns]
        if unknowns:
            lines.append("**Unknown or not evidenced**")
            lines += [f"- {name}: {text}" for name, text in unknowns[:12]]
            lines.append("")
    if reviews and reviews.findings:
        basis = Counter(f.basis for f in reviews.findings)
        lines.append(
            "**Customer feedback by basis:** "
            f"{basis.get('quoted', 0)} quoted, {basis.get('reported', 0)} reported "
            f"(each with a source), {basis.get('inferred', 0)} inferred (no source)."
        )
        inferred = [f for f in reviews.findings if f.basis == "inferred"]
        for f in inferred[:5]:
            lines.append(f"- Inferred, unsupported by a source: {f.competitor}: {f.text}")
        lines.append("")
    elif reviews is not None:
        lines += ["**Customer feedback:** no attributable findings were retrieved.", ""]
    if strategy and (strategy.recommended_offer or strategy.recommended_price):
        lines += [
            "**Recommendation (not a verified fact)**",
            f"- Offer: {strategy.recommended_offer or 'unknown'}",
            f"- Positioning: {strategy.positioning_line or 'unknown'}",
            f"- Price (Recommendation): {strategy.recommended_price or 'unknown'}",
            "",
        ]
    if validation.links:
        states = Counter(link.status for link in validation.links)
        lines.append(
            "**Link status (HTTP reachability only; not evidence verification):** "
            + ", ".join(f"{n} {state}" for state, n in sorted(states.items()))
            + "."
        )
        lines.append("")
    lines.append(
        f"**Evidence ledger:** {len(ledger)} URL(s) returned by tools; "
        f"{validation.verified_prices} competitor(s) with a verified price."
    )
    return "\n".join(lines).rstrip() + "\n"


def build_final_report(
    writer_markdown: str,
    validation: ValidationReport,
    competitors: CompetitorSet | None,
    reviews: ReviewSet | None,
    strategy: StrategyOutput | None,
    ledger: EvidenceLedger,
    run_id: str,
) -> str:
    """Final text: header, writer body (tagged when not validated) and generated summary."""
    body = writer_markdown.strip()
    passed = validation.state == "validated_pass"
    if not passed:
        body = tag_unsupported_urls(body, report_unsupported_urls(body, ledger))
        if competitors is not None:
            body = tag_unverified_prices(body, competitors.competitors)
    header = pass_header(run_id) if passed else partial_header(validation)
    summary = verification_summary(validation, competitors, reviews, strategy, ledger)
    return f"{header}\n{body}\n\n{summary}"


def report_filenames(state: str) -> tuple[str, str]:
    """(markdown, pdf) names; partial reports always carry -PARTIAL (PRP 7.1)."""
    if state == "validated_pass":
        return "report.md", "report.pdf"
    return "report-PARTIAL.md", "report-PARTIAL.pdf"


def section_keys(markdown: str) -> list[str]:
    """Canonical section keys in the order the headings appear."""
    keys = (section_key(heading) for heading, _ in split_top_sections(markdown))
    return [k for k in keys if k is not None]
