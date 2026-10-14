"""Parse agent outputs and ground them against the evidence ledger.

Rules (PRP G1, G2): an item the tools never returned is never presented as verified. Items are
downgraded to `unknown`/`inferred` and the downgrade is reported, not hidden. This is the M3
subset; the full acceptance gate and report validators arrive in M4.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from launchscout.evidence import EvidenceLedger
from launchscout.schemas import (
    Competitor,
    CompetitorSet,
    Price,
    ReviewFinding,
    ReviewSet,
    StrategyOutput,
)

_URL_RE = re.compile(r"https?://[^\s)>\]\"'`]+")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3})")
_TRAILING = ".,;:!?"


class Grounded(BaseModel):
    """Parsed (and possibly downgraded) output plus a list of human-readable issues."""

    issues: list[str] = Field(default_factory=list)


class GroundedCompetitors(Grounded):
    value: CompetitorSet | None = None


class GroundedReviews(Grounded):
    value: ReviewSet | None = None


class GroundedStrategy(Grounded):
    value: StrategyOutput | None = None


def extract_json(raw: str) -> dict[str, Any] | None:
    """Return the first top-level JSON object in `raw` (tolerates fences and chatter)."""
    if not raw:
        return None
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    decoder = json.JSONDecoder()
    for start in (m.start() for m in re.finditer(r"\{", text)):
        try:
            value, _ = decoder.raw_decode(text[start:])
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _date(value: Any) -> date | None:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _coerce_price(raw: Any, issues: list[str], name: str) -> Price:
    if not isinstance(raw, dict):
        return Price()
    status = raw.get("status") if raw.get("status") in ("verified", "unknown") else "unknown"
    amount = raw.get("amount")
    try:
        amount = float(amount) if amount is not None else None
    except (TypeError, ValueError):
        amount = None
    fields = {
        "amount": amount,
        "currency": raw.get("currency") or None,
        "unit": raw.get("unit") or None,
        "pack_size": raw.get("pack_size") or None,
        "evidence_url": raw.get("evidence_url") or None,
        "accessed_on": _date(raw.get("accessed_on")),
    }
    required = ("amount", "currency", "unit", "evidence_url", "accessed_on")
    if status == "verified" and any(fields[k] in (None, "") for k in required):
        issues.append(f"{name}: price marked verified but incomplete; downgraded to unknown")
        return Price()
    return Price(status=status, **fields)  # type: ignore[arg-type]


def amount_in_text(amount: float, text: str) -> bool:
    """True if `amount` appears as a standalone number in `text` (commas and .00 tolerated)."""
    if not text:
        return False
    plain = _THOUSANDS.sub("", text)
    number = f"{amount:.2f}".rstrip("0").rstrip(".")
    tail = "0*" if "." in number else r"(?:\.0+)?"
    pattern = rf"(?<![\d.]){re.escape(number)}{tail}(?![\d]|\.\d)"
    return re.search(pattern, plain) is not None


def parse_competitors(raw: str) -> GroundedCompetitors:
    data = extract_json(raw)
    if data is None or not isinstance(data.get("competitors"), list):
        return GroundedCompetitors(issues=["competitor output was not valid JSON"])
    issues: list[str] = []
    items: list[Competitor] = []
    for entry in data["competitors"]:
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("url"):
            issues.append("a competitor entry lacked a name or URL and was dropped")
            continue
        name = str(entry["name"])
        items.append(
            Competitor(
                name=name,
                url=str(entry["url"]),
                location_relevance=str(entry.get("location_relevance") or ""),
                offer=str(entry.get("offer") or ""),
                price=_coerce_price(entry.get("price"), issues, name),
                channels=[str(c) for c in entry.get("channels") or [] if c],
                evidence_urls=[str(u) for u in entry.get("evidence_urls") or [] if u],
                accessed_on=_date(entry.get("accessed_on")),
                unknowns=[str(u) for u in entry.get("unknowns") or [] if u],
            )
        )
    if len(items) > 5:
        issues.append(f"{len(items)} competitors returned; kept the first 5")
        items = items[:5]
    shortfall = data.get("shortfall_reason") or None
    if len(items) < 3 and not (shortfall or "").strip():
        shortfall = "Fewer than 3 competitors were found; the agent gave no reason."
        issues.append("fewer than 3 competitors and no reason given by the agent")
    try:
        value = CompetitorSet(
            competitors=items, notes=str(data.get("notes") or ""), shortfall_reason=shortfall
        )
    except ValidationError as exc:
        return GroundedCompetitors(issues=issues + [f"competitor set invalid: {exc.error_count()}"])
    return GroundedCompetitors(value=value, issues=issues)


def ground_competitors(result: GroundedCompetitors, ledger: EvidenceLedger) -> GroundedCompetitors:
    """Downgrade anything the tools never returned. Items are kept and tagged, not dropped."""
    if result.value is None:
        return result
    issues = list(result.issues)
    competitors: list[Competitor] = []
    for comp in result.value.competitors:
        unknowns = list(comp.unknowns)
        if not (ledger.contains(comp.url) or ledger.host_seen(comp.url)):
            unknowns.append("unverified: site URL was not returned by any tool")
            issues.append(f"{comp.name}: site URL not found in tool results")
        kept = [u for u in comp.evidence_urls if ledger.contains(u)]
        dropped = [u for u in comp.evidence_urls if u not in kept]
        if dropped:
            issues.append(f"{comp.name}: {len(dropped)} evidence URL(s) not in tool results")
        if not kept:
            unknowns.append("unverified: no evidence URL was found in tool results")
        price = comp.price
        if price.status == "verified" and not ledger.contains(price.evidence_url):
            issues.append(f"{comp.name}: price evidence URL not in tool results; set to unknown")
            unknowns.append("price unknown: evidence URL was not returned by any tool")
            price = Price()
        elif price.status == "verified" and price.amount is not None:
            entry = ledger.get(price.evidence_url)
            evidence_text = (entry.text or entry.excerpt) if entry else ""
            if not amount_in_text(price.amount, evidence_text):
                issues.append(
                    f"{comp.name}: amount {price.amount:g} not found in the stored text of its "
                    "evidence page; price set to unknown"
                )
                unknowns.append("price unknown: amount not found in the stored evidence text")
                price = Price()
        competitors.append(
            comp.model_copy(update={"evidence_urls": kept, "unknowns": unknowns, "price": price})
        )
    value = result.value.model_copy(update={"competitors": competitors})
    return GroundedCompetitors(value=value, issues=issues)


def parse_reviews(raw: str, ledger: EvidenceLedger) -> GroundedReviews:
    data = extract_json(raw)
    if data is None or not isinstance(data.get("findings"), list):
        return GroundedReviews(issues=["review output was not valid JSON"])
    issues: list[str] = []
    findings: list[ReviewFinding] = []
    for entry in data["findings"]:
        if not isinstance(entry, dict) or not entry.get("text") or not entry.get("competitor"):
            issues.append("a review finding lacked text or competitor and was dropped")
            continue
        kind = entry.get("kind") if entry.get("kind") in ("praise", "complaint") else None
        basis = entry.get("basis")
        if basis not in ("quoted", "reported", "inferred"):
            basis = None
        if kind is None:
            issues.append("a review finding had an invalid kind and was dropped")
            continue
        source = entry.get("source_url") or None
        basis = basis or "inferred"
        if basis in ("quoted", "reported") and not ledger.contains(source):
            issues.append(
                f"{entry['competitor']}: {basis} finding has no source in tool results; "
                "relabelled inferred"
            )
            basis, source = "inferred", None
        findings.append(
            ReviewFinding(
                competitor=str(entry["competitor"]),
                kind=kind,
                text=str(entry["text"]),
                basis=basis,
                source_url=source,
            )
        )
    value = ReviewSet(
        findings=findings,
        per_competitor_summary=[str(s) for s in data.get("per_competitor_summary") or []],
        gaps=[str(g) for g in data.get("gaps") or []],
    )
    return GroundedReviews(value=value, issues=issues)


def parse_strategy(raw: str, ledger: EvidenceLedger) -> GroundedStrategy:
    data = extract_json(raw)
    if data is None:
        return GroundedStrategy(issues=["strategy output was not valid JSON"])
    issues: list[str] = []
    refs_in = [str(r) for r in data.get("evidence_refs") or [] if r]
    refs = [r for r in refs_in if ledger.contains(r)]
    if len(refs) != len(refs_in):
        issues.append(f"{len(refs_in) - len(refs)} strategy evidence ref(s) not in tool results")
    matrix = [
        {str(k): str(v) for k, v in row.items()}
        for row in data.get("comparison_matrix") or []
        if isinstance(row, dict)
    ]
    value = StrategyOutput(
        comparison_matrix=matrix,
        market_gap=str(data.get("market_gap") or ""),
        evidence_refs=refs,
        recommended_offer=str(data.get("recommended_offer") or ""),
        positioning_line=str(data.get("positioning_line") or ""),
        recommended_price=str(data.get("recommended_price") or ""),
        rationale=str(data.get("rationale") or ""),
    )
    return GroundedStrategy(value=value, issues=issues)


def report_unsupported_urls(markdown: str, ledger: EvidenceLedger) -> list[str]:
    """URLs in the report that no tool ever returned (candidate fabrications)."""
    seen: list[str] = []
    for match in _URL_RE.findall(markdown):
        url = match.rstrip(_TRAILING)
        if url not in seen and not ledger.contains(url):
            seen.append(url)
    return seen
