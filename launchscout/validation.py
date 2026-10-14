"""Deterministic report validation and the acceptance gate (PRP sections 7 and 7.1).

Pure Python: no model calls, no network. Inputs are the stored structured outputs, the evidence
ledger and the report text, so a run can be re-validated later from its artifacts alone.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from launchscout.evidence import EvidenceLedger
from launchscout.grounding import report_unsupported_urls
from launchscout.links import LinkStatus
from launchscout.schemas import Acceptance, Competitor, CompetitorSet

ReportState = Literal["validated_pass", "partial_failed_acceptance", "failed_no_report"]

# (key, canonical title, keywords checked in this order against a normalised heading)
SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("key_competitors", "Key Competitors"),
    ("complaints", "What Customers Complain About"),
    ("market_gap", "Market Gap"),
    ("positioning", "Recommended Positioning"),
    ("launch_plan", "30-Day Launch Plan"),
    ("sources", "Sources"),
)
_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("sources", ("sources",)),
    ("launch_plan", ("launch plan", "30-day", "30 day")),
    ("complaints", ("complain", "pain point")),
    ("market_gap", ("market gap",)),
    ("positioning", ("positioning",)),
    ("key_competitors", ("key competitors", "competitors")),
)
_AMOUNT_RE = re.compile(
    r"(?:₹|Rs\.?|INR|\$|USD|€|EUR)\s?(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s?(?:₹|INR|Rs\.?)",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


class RuleResult(BaseModel):
    id: str
    title: str
    status: Literal["pass", "fail", "info"]
    detail: str = ""
    items: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    state: ReportState
    acceptance: Acceptance
    rules: list[RuleResult] = Field(default_factory=list)
    section_keys: list[str] = Field(default_factory=list)
    competitor_rows: int = 0
    verified_prices: int = 0
    eligible_competitors: int = 0
    links: list[LinkStatus] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)

    @property
    def failed_rules(self) -> list[RuleResult]:
        return [r for r in self.rules if r.status == "fail"]


# ---- parsing helpers ----------------------------------------------------------------------


def _normalise_heading(text: str) -> str:
    text = re.sub(r"^[\d.\s)(-]+", "", text.strip().lower())
    return re.sub(r"[*_`]", "", text).strip()


def section_key(heading: str) -> str | None:
    norm = _normalise_heading(heading)
    for key, words in _KEYWORDS:
        if any(w in norm for w in words):
            return key
    return None


def split_top_sections(markdown: str) -> list[tuple[str, str]]:
    """Top-level sections as (heading text, body). Level 2 headings; level 1 if none exist."""
    lines = markdown.splitlines()
    headings: list[tuple[int, int, str]] = []
    fenced = False
    for index, line in enumerate(lines):
        if line.strip().startswith("```"):
            fenced = not fenced
        if fenced:
            continue
        match = _HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2)))
    levels = {level for _, level, _ in headings}
    top = 2 if 2 in levels else (1 if 1 in levels else None)
    if top is None:
        return []
    marks = [(i, text) for i, level, text in headings if level == top]
    sections: list[tuple[str, str]] = []
    for pos, (start, text) in enumerate(marks):
        end = marks[pos + 1][0] if pos + 1 < len(marks) else len(lines)
        sections.append((text, "\n".join(lines[start + 1 : end])))
    return sections


def table_rows(body: str) -> list[list[str]]:
    """Data rows of Markdown tables in `body` (header and separator rows excluded)."""
    rows: list[list[str]] = []
    block: list[list[str]] = []

    def flush() -> None:
        # first row is the header
        rows.extend(block[1:])
        block.clear()

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) or not c for c in cells):
                continue
            block.append(cells)
        elif block:
            flush()
    if block:
        flush()
    return rows


_ACK_RE = re.compile(r"unknown|not verified|unverified|not attributable|not evidenced", re.I)


def amounts_in(text: str, skip_acknowledged: bool = False) -> list[float]:
    """Currency amounts in `text`.

    With `skip_acknowledged`, amounts the text itself labels as unknown/unverified within a
    short window are ignored: saying "unknown; search results showed Rs 199" is honest.
    """
    values: list[float] = []
    for match in _AMOUNT_RE.finditer(text):
        if skip_acknowledged:
            window = text[max(0, match.start() - 70) : match.end() + 70]
            if _ACK_RE.search(window):
                continue
        raw = match.group(1) or match.group(2)
        try:
            values.append(float(raw.replace(",", "")))
        except ValueError:
            continue
    return values


# ---- rules --------------------------------------------------------------------------------


def _rule_sections(sections: list[tuple[str, str]]) -> tuple[RuleResult, list[str]]:
    keys = [section_key(heading) for heading, _ in sections]
    expected = [k for k, _ in SECTION_ORDER]
    problems: list[str] = []
    seen = [k for k in keys if k]
    for key, title in SECTION_ORDER:
        if key not in seen:
            problems.append(f"missing section: {title}")
    unknown = [h for (h, _), k in zip(sections, keys, strict=True) if k is None]
    problems += [f"unexpected top-level section: {h}" for h in unknown]
    if seen != expected and not any(p.startswith("missing") for p in problems):
        if len(set(seen)) != len(seen):
            problems.append("a section appears more than once")
        else:
            problems.append("sections are not in the required order")
    status = "pass" if not problems else "fail"
    detail = "Six sections present, in order." if status == "pass" else "; ".join(problems)
    return RuleResult(id="R1", title="Six sections in order", status=status, detail=detail,
                      items=problems), [k for k in seen]


def _body_for(sections: list[tuple[str, str]], key: str) -> str:
    for heading, body in sections:
        if section_key(heading) == key:
            return body
    return ""


def _rule_competitor_rows(body: str) -> tuple[RuleResult, int]:
    rows = [r for r in table_rows(body) if any(r)]
    status = "pass" if len(rows) >= 3 else "fail"
    detail = f"{len(rows)} competitor row(s) in the Key Competitors table (3 required)."
    return RuleResult(id="R2", title="At least 3 competitor rows", status=status,
                      detail=detail), len(rows)


def _rule_urls_in_ledger(markdown: str, ledger: EvidenceLedger) -> RuleResult:
    missing = report_unsupported_urls(markdown, ledger)
    return RuleResult(
        id="R3",
        title="Every URL in the report was returned by a tool",
        status="pass" if not missing else "fail",
        detail="All report URLs are in the evidence ledger."
        if not missing
        else f"{len(missing)} URL(s) were never returned by any tool.",
        items=missing,
    )


def _rule_prices(body: str, competitors: list[Competitor]) -> RuleResult:
    problems: list[str] = []
    rows = [r for r in table_rows(body) if any(r)]
    by_name = {c.name.casefold().strip(): c for c in competitors}
    for row in rows:
        row_text = " ".join(row)
        comp = next((c for key, c in by_name.items() if key and key in row_text.casefold()), None)
        found = amounts_in(row_text, skip_acknowledged=True)
        if comp is None or not found:
            continue
        if comp.price.status != "verified":
            problems.append(f"{comp.name}: a price appears in the report but is not verified")
        elif comp.price.amount is not None and not any(
            abs(v - comp.price.amount) < 0.005 for v in found
        ):
            problems.append(f"{comp.name}: report amount differs from the verified price")
    return RuleResult(
        id="R4",
        title="Report prices match verified evidence",
        status="pass" if not problems else "fail",
        detail="Every price in the competitor table matches a verified price or is unknown."
        if not problems
        else "; ".join(problems),
        items=problems,
    )


def _rule_launch_plan(body: str) -> RuleResult:
    missing = [f"Week {n}" for n in (1, 2, 3, 4) if not re.search(rf"week\s*{n}\b", body, re.I)]
    return RuleResult(
        id="R5",
        title="30-day plan covers Weeks 1-4",
        status="pass" if not missing else "fail",
        detail="Weeks 1-4 present." if not missing else f"Missing: {', '.join(missing)}.",
        items=missing,
    )


def _rule_recommendation_label(body: str) -> RuleResult:
    ok = bool(re.search(r"recommendation", body, re.I))
    return RuleResult(
        id="R6",
        title="Proposed price labelled Recommendation",
        status="pass" if ok else "fail",
        detail="Recommendation label present."
        if ok
        else "The positioning section does not label the price as a Recommendation.",
    )


def _rule_sources_cover(body: str, competitors: list[Competitor], ledger: EvidenceLedger
                        ) -> RuleResult:
    from launchscout.evidence import normalize_url

    present = {normalize_url(u) for u in re.findall(r"https?://[^\s)>\]\"'`]+", body)}
    missing: list[str] = []
    for comp in competitors:
        if comp.price.status == "verified" and comp.price.evidence_url:
            if normalize_url(comp.price.evidence_url.rstrip(".,;:")) not in present:
                missing.append(f"{comp.name}: price evidence URL not listed in Sources")
        for url in comp.evidence_urls:
            if ledger.contains(url) and normalize_url(url.rstrip(".,;:")) not in present:
                missing.append(f"{comp.name}: evidence URL not listed in Sources")
    return RuleResult(
        id="R7",
        title="Sources cover every competitor and verified price",
        status="pass" if not missing else "fail",
        detail="All competitor and price evidence URLs are listed."
        if not missing
        else f"{len(missing)} source(s) missing from the Sources section.",
        items=missing,
    )


def _rule_links(links: list[LinkStatus]) -> RuleResult:
    broken = [f"{lk.url} ({lk.detail})" for lk in links if lk.status == "broken"]
    blocked = [lk.url for lk in links if lk.status == "blocked"]
    unchecked = [lk.url for lk in links if lk.status == "not_checked"]
    if broken:
        return RuleResult(id="R8", title="Links reachable", status="fail",
                          detail=f"{len(broken)} link(s) are broken.", items=broken)
    note = []
    if blocked:
        note.append(f"{len(blocked)} refused automated access (reachable, not verifiable)")
    if unchecked:
        note.append(f"{len(unchecked)} not checked")
    detail = "No broken links." + (" " + "; ".join(note) + "." if note else "")
    return RuleResult(id="R8", title="Links reachable", status="pass", detail=detail,
                      items=blocked + unchecked)


# ---- gate ---------------------------------------------------------------------------------


def evaluate_gate(competitors: CompetitorSet | None, ledger: EvidenceLedger
                  ) -> tuple[list[str], int, int]:
    """Acceptance-gate reasons plus (eligible competitors, verified prices)."""
    if competitors is None:
        return ["competitor research output is missing or could not be parsed"], 0, 0
    eligible = [
        c for c in competitors.competitors if c.name.strip() and c.url.strip() and c.evidence_urls
    ]
    verified = [
        c
        for c in eligible
        if c.price.status == "verified" and ledger.contains(c.price.evidence_url)
    ]
    reasons: list[str] = []
    if len(eligible) < 3:
        reasons.append(
            f"only {len(eligible)} competitor(s) have a name, URL and evidence URL (3 required)"
        )
    if len(verified) < 3:
        reasons.append(
            f"only {len(verified)} competitor(s) have a verified price with evidence (3 required)"
        )
    return reasons, len(eligible), len(verified)


def validate_report(
    markdown: str | None,
    competitors: CompetitorSet | None,
    ledger: EvidenceLedger,
    links: list[LinkStatus] | None = None,
    review_counts: dict[str, int] | None = None,
) -> ValidationReport:
    """Run every deterministic rule and the acceptance gate. Never calls a model."""
    links = links or []
    if not markdown or not markdown.strip():
        return ValidationReport(
            state="failed_no_report",
            acceptance=Acceptance(result="fail", reasons=["no report was produced"]),
            rules=[RuleResult(id="R0", title="Report exists", status="fail",
                              detail="No report text was produced.")],
        )
    sections = split_top_sections(markdown)
    comp_list = competitors.competitors if competitors else []
    r1, keys = _rule_sections(sections)
    r2, row_count = _rule_competitor_rows(_body_for(sections, "key_competitors"))
    rules = [
        r1,
        r2,
        _rule_urls_in_ledger(markdown, ledger),
        _rule_prices(_body_for(sections, "key_competitors"), comp_list),
        _rule_launch_plan(_body_for(sections, "launch_plan")),
        _rule_recommendation_label(_body_for(sections, "positioning")),
        _rule_sources_cover(_body_for(sections, "sources"), comp_list, ledger),
        _rule_links(links),
    ]
    gate_reasons, eligible, verified = evaluate_gate(competitors, ledger)
    reasons = list(gate_reasons)
    for rule in rules:
        if rule.status == "fail":
            reasons.append(f"{rule.id} {rule.title}: {rule.detail}")
    passed = not reasons
    return ValidationReport(
        state="validated_pass" if passed else "partial_failed_acceptance",
        acceptance=Acceptance(result="pass" if passed else "fail", reasons=reasons),
        rules=rules,
        section_keys=keys,
        competitor_rows=row_count,
        verified_prices=verified,
        eligible_competitors=eligible,
        links=links,
        counts=review_counts or {},
    )
