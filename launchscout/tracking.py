"""Competitor change tracking: deterministic, offline comparison of two saved research runs.

Inputs are `RunSnapshot`s rebuilt from `runs/<id>/` (the existing saved-run structures). Nothing
here calls a model, a search or scrape tool, CrewAI or any network service, and nothing is
written. A difference between two snapshots describes what each research run *found*; it is
never presented as proof of a real-world business change.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from launchscout.evidence import host_of, normalize_url
from launchscout.runner import RunSnapshot
from launchscout.schemas import Competitor, Price

# Hosts that identify a platform, not a business: never used on their own to match competitors.
GENERIC_HOSTS = frozenset(
    {
        "instagram.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "youtube.com",
        "wa.me",
        "linktr.ee",
        "google.com",
        "maps.google.com",
        "zomato.com",
        "swiggy.com",
    }
)
SUBSCRIPTION_RE = re.compile(r"subscri|plan|weekly|daily|trial|monthly", re.I)
NEW = "new"
NOT_OBSERVED = "not_observed"
CHANGED = "changed"
REVIEW = "review"
UNCHANGED = "unchanged"
STATUS_LABEL = {
    NEW: "Newly observed",
    NOT_OBSERVED: "Not observed in latest run",
    CHANGED: "Changed",
    REVIEW: "Needs review (research description differs, real-world change not verified)",
    UNCHANGED: "No change observed",
}
STATUS_ORDER = (NEW, NOT_OBSERVED, CHANGED, REVIEW, UNCHANGED)

DESCRIPTION_DIFFERS = "Research description differs — real-world change not verified"

ChangeKind = Literal["offering", "subscription", "channels", "price", "evidence"]


class Change(BaseModel):
    kind: ChangeKind
    label: str
    before: str = ""
    after: str = ""
    certainty: Literal["observed", "inconclusive"] = "observed"
    sources: list[str] = Field(default_factory=list)


class CompetitorChange(BaseModel):
    name: str
    status: str
    label: str
    changes: list[Change] = Field(default_factory=list)
    baseline_sources: list[str] = Field(default_factory=list)
    latest_sources: list[str] = Field(default_factory=list)


class SnapshotInfo(BaseModel):
    run_id: str
    started_at: datetime
    report_state: str | None
    mode: str
    model_name: str | None
    competitor_count: int
    verified_prices: int


class Comparison(BaseModel):
    eligible: bool
    reasons: list[str] = Field(default_factory=list)
    idea: str = ""
    city: str = ""
    baseline: SnapshotInfo | None = None
    latest: SnapshotInfo | None = None
    rows: list[CompetitorChange] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(1 for r in self.rows if r.status == status)


# ----------------------------------------------------------------------------- normalisation
def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", (text or "").casefold()).split())


def _norm_currency(value: str | None) -> str:
    cleaned = (value or "").strip().upper().replace(".", "")
    return {"₹": "INR", "RS": "INR", "RUPEES": "INR", "$": "USD"}.get(cleaned, cleaned)


def _scope(snapshot: RunSnapshot) -> tuple[str, str, str]:
    i = snapshot.input
    return _norm(i.idea), _norm(i.city), _norm(i.target_customer)


def _same_business(a: Competitor, b: Competitor) -> bool:
    if _norm(a.name) and _norm(a.name) == _norm(b.name):
        return True
    host_a, host_b = host_of(a.url), host_of(b.url)
    return bool(host_a) and host_a == host_b and host_a not in GENERIC_HOSTS


def _sources(comp: Competitor) -> list[str]:
    urls = list(comp.evidence_urls) or [comp.url]  # homepage only when nothing else
    if comp.price.evidence_url:
        urls.append(comp.price.evidence_url)
    return sorted({normalize_url(u) for u in urls if u})


def _subscription(comp: Competitor) -> str:
    parts = re.split(r"(?<=[.;])\s+", comp.offer or "")
    return " ".join(p.strip() for p in parts if SUBSCRIPTION_RE.search(p))


def _price_text(price: Price) -> str:
    if price.status != "verified" or price.amount is None:
        return "not verified"
    pack = f", pack {price.pack_size}" if price.pack_size else ""
    when = f", accessed {price.accessed_on.isoformat()}" if price.accessed_on else ""
    return f"{_norm_currency(price.currency)} {price.amount:g} per {price.unit}{pack}{when}"


def _complete(price: Price) -> bool:
    return bool(
        price.status == "verified"
        and price.amount is not None
        and price.currency
        and price.unit
        and price.evidence_url
        and price.accessed_on
    )


# ----------------------------------------------------------------------------- change detection
def price_change(old: Price, new: Price) -> Change | None:
    """Classify a price difference conservatively (see module docstring).

    A *verified price change* needs two complete, evidence-backed amounts with the same
    currency, unit and pack size. Anything else is labelled as a verification change or as
    insufficient evidence, never as a market price movement.
    """
    sources = [u for u in (old.evidence_url, new.evidence_url) if u]
    before, after = _price_text(old), _price_text(new)
    old_ok, new_ok = _complete(old), _complete(new)
    if old_ok and new_ok:
        same_basis = (
            _norm_currency(old.currency) == _norm_currency(new.currency)
            and _norm(old.unit or "") == _norm(new.unit or "")
            and _norm(old.pack_size or "") == _norm(new.pack_size or "")
        )
        if not same_basis:
            return Change(
                kind="price",
                label="Insufficient evidence: prices are not comparable (currency, unit or pack "
                "size differs)",
                before=before,
                after=after,
                certainty="inconclusive",
                sources=sources,
            )
        if old.amount == new.amount:
            return None
        delta = float(new.amount) - float(old.amount)  # type: ignore[arg-type]
        pct = delta / float(old.amount) * 100 if old.amount else 0.0
        return Change(
            kind="price",
            label=f"Verified price change ({delta:+g}, {pct:+.1f}%)",
            before=before,
            after=after,
            certainty="observed",
            sources=sources,
        )
    if old_ok != new_ok:
        return Change(
            kind="price",
            label="Price verification changed",
            before=before,
            after=after,
            certainty="inconclusive",
            sources=sources,
        )
    if old.status == "verified" or new.status == "verified":
        return Change(  # a "verified" price missing amount/unit/source in a snapshot
            kind="price",
            label="Insufficient evidence: a verified price lacks amount, unit or source",
            before=before,
            after=after,
            certainty="inconclusive",
            sources=sources,
        )
    return None  # no verified price in either snapshot: nothing to compare


def _compare_pair(old: Competitor, new: Competitor) -> list[Change]:
    changes: list[Change] = []
    if _norm(old.offer) != _norm(new.offer):
        changes.append(
            Change(
                kind="offering",
                label=f"Offering: {DESCRIPTION_DIFFERS}",
                before=old.offer or "not evidenced",
                after=new.offer or "not evidenced",
                certainty="inconclusive",
                sources=sorted(set(_sources(old)) | set(_sources(new))),
            )
        )
    old_sub, new_sub = _subscription(old), _subscription(new)
    if _norm(old_sub) != _norm(new_sub):
        changes.append(
            Change(
                kind="subscription",
                label=f"Subscription: {DESCRIPTION_DIFFERS}",
                before=old_sub or "not evidenced",
                after=new_sub or "not evidenced",
                certainty="inconclusive",
                sources=sorted(set(_sources(old)) | set(_sources(new))),
            )
        )
    old_ch = {_norm(c): c for c in old.channels if _norm(c)}
    new_ch = {_norm(c): c for c in new.channels if _norm(c)}
    if set(old_ch) != set(new_ch):
        added = sorted(new_ch[k] for k in set(new_ch) - set(old_ch))
        removed = sorted(old_ch[k] for k in set(old_ch) - set(new_ch))
        label = f"Channels: {DESCRIPTION_DIFFERS}"
        if added:
            label += f" (added: {', '.join(added)})"
        if removed:
            label += f" (not recorded now: {', '.join(removed)})"
        changes.append(
            Change(
                kind="channels",
                label=label,
                before="; ".join(sorted(old_ch.values())) or "none recorded",
                after="; ".join(sorted(new_ch.values())) or "none recorded",
                certainty="inconclusive",
                sources=sorted(set(_sources(old)) | set(_sources(new))),
            )
        )
    price = price_change(old.price, new.price)
    if price is not None:
        changes.append(price)
    old_src, new_src = set(_sources(old)), set(_sources(new))
    if old_src != new_src:
        gained, lost = sorted(new_src - old_src), sorted(old_src - new_src)
        changes.append(
            Change(
                kind="evidence",
                label=f"Evidence availability differs ({len(gained)} new, {len(lost)} not "
                "re-found); this describes research coverage, not the business",
                before=f"{len(old_src)} source URL(s)",
                after=f"{len(new_src)} source URL(s)",
                certainty="inconclusive",
                sources=[*gained, *lost],
            )
        )
    return changes


def _row_for_pair(old: Competitor, new: Competitor) -> CompetitorChange:
    changes = _compare_pair(old, new)
    # Only a verified price change is established by the saved evidence. Text differences in
    # research descriptions (offering, subscription, channels) and evidence coverage are
    # inconclusive and never count as a changed competitor.
    substantive = [c for c in changes if c.kind == "price" and c.certainty == "observed"]
    if substantive:
        status = CHANGED
    elif changes:
        status = REVIEW
    else:
        status = UNCHANGED
    return CompetitorChange(
        name=new.name,
        status=status,
        label=STATUS_LABEL[status],
        changes=changes,
        baseline_sources=_sources(old),
        latest_sources=_sources(new),
    )


# ----------------------------------------------------------------------------- comparison
def _info(snapshot: RunSnapshot) -> SnapshotInfo:
    comps = snapshot.competitors.competitors if snapshot.competitors else []
    verified = sum(1 for c in comps if _complete(c.price))
    return SnapshotInfo(
        run_id=snapshot.run_id,
        started_at=snapshot.started_at,
        report_state=snapshot.validation.state if snapshot.validation else None,
        mode=snapshot.mode.value,
        model_name=snapshot.model_name,
        competitor_count=len(comps),
        verified_prices=verified,
    )


def _ineligible(*reasons: str, idea: str = "", city: str = "") -> Comparison:
    return Comparison(eligible=False, reasons=list(reasons), idea=idea, city=city)


def check_compatibility(baseline: RunSnapshot | None, latest: RunSnapshot | None) -> list[str]:
    """Reasons a comparison is not meaningful (empty list = compatible)."""
    if baseline is None or latest is None:
        return ["A saved run could not be read, so no comparison is possible."]
    reasons: list[str] = []
    if baseline.run_id == latest.run_id:
        reasons.append("Baseline and latest are the same run.")
    names = ("idea", "city", "target customer")
    differing = [
        n for n, a, b in zip(names, _scope(baseline), _scope(latest), strict=True) if a != b
    ]
    if differing:
        reasons.append(
            "The runs cover different research scopes (" + ", ".join(differing) + " differ), "
            "so their competitors are not comparable."
        )
    for label, snap in (("Baseline", baseline), ("Latest", latest)):
        if snap.competitors is None or not snap.competitors.competitors:
            reasons.append(f"{label} run has no competitor findings to compare.")
        if snap.status in ("failed", "created", "running"):
            reasons.append(f"{label} run did not finish (status: {snap.status}).")
    if baseline.run_id != latest.run_id and baseline.started_at >= latest.started_at:
        reasons.append("The baseline run is not older than the latest run.")
    return reasons


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def compare_snapshots(baseline: RunSnapshot | None, latest: RunSnapshot | None) -> Comparison:
    """Compare two saved runs of the same research scope. Pure and deterministic."""
    reasons = check_compatibility(baseline, latest)
    idea = latest.input.idea if latest else ""
    city = latest.input.city if latest else ""
    if reasons or baseline is None or latest is None:
        return _ineligible(*reasons, idea=idea, city=city)
    assert baseline.competitors is not None and latest.competitors is not None
    old_list = list(baseline.competitors.competitors)
    new_list = list(latest.competitors.competitors)
    rows: list[CompetitorChange] = []
    matched_old: set[int] = set()
    for new in new_list:
        index = next(
            (
                i
                for i, old in enumerate(old_list)
                if i not in matched_old and _same_business(old, new)
            ),
            None,
        )
        if index is None:
            rows.append(
                CompetitorChange(
                    name=new.name,
                    status=NEW,
                    label=STATUS_LABEL[NEW],
                    latest_sources=_sources(new),
                )
            )
        else:
            matched_old.add(index)
            rows.append(_row_for_pair(old_list[index], new))
    for i, old in enumerate(old_list):
        if i not in matched_old:
            rows.append(
                CompetitorChange(
                    name=old.name,
                    status=NOT_OBSERVED,
                    label=STATUS_LABEL[NOT_OBSERVED],
                    baseline_sources=_sources(old),
                )
            )
    rows.sort(key=lambda r: (STATUS_ORDER.index(r.status), r.name.casefold()))
    info_old, info_new = _info(baseline), _info(latest)
    limits = [
        "Differences describe what each research run found. They do not establish a change in "
        "the real market, and a competitor missing from a run is not evidence that it closed."
    ]
    for label, info in (("Baseline", info_old), ("Latest", info_new)):
        if info.report_state != "validated_pass":
            state = info.report_state or "no validation record (legacy run)"
            limits.append(
                f"{label} run was not a fully validated report ({state}); its competitor "
                "coverage may be incomplete."
            )
    if info_old.competitor_count != info_new.competitor_count:
        limits.append(
            f"The runs found a different number of competitors ({info_old.competitor_count} vs "
            f"{info_new.competitor_count}); absences may reflect search coverage."
        )
    if info_old.mode != info_new.mode:
        limits.append(
            f"The runs used different research modes ({info_old.mode} vs {info_new.mode})."
        )
    if info_old.model_name != info_new.model_name:
        limits.append("The runs used different models, which can change what is found.")
    gap = latest.started_at - baseline.started_at
    if gap.total_seconds() < 86400:
        hours = gap.total_seconds() / 3600
        limits.append(
            f"The runs were made {hours:.1f} hours apart; differences are more likely research "
            "variance than market change."
        )
    return Comparison(
        eligible=True,
        idea=latest.input.idea,
        city=latest.input.city,
        baseline=info_old,
        latest=info_new,
        rows=rows,
        limitations=limits,
    )


# ----------------------------------------------------------------------------- export
def to_markdown(comparison: Comparison) -> str:
    """Deterministic Markdown change summary (no generation timestamp, no external data)."""
    lines = ["# Competitor change summary", ""]
    if not comparison.eligible:
        lines += ["**Comparison unavailable.**", ""]
        lines += [f"- {r}" for r in comparison.reasons]
        return "\n".join(lines) + "\n"
    old, new = comparison.baseline, comparison.latest
    assert old is not None and new is not None
    lines += [
        f"- **Business idea:** {comparison.idea}",
        f"- **Market:** {comparison.city}",
        f"- **Baseline run:** `{old.run_id}` ({_stamp(old.started_at)}, "
        f"{old.report_state or 'no validation record'})",
        f"- **Latest run:** `{new.run_id}` ({_stamp(new.started_at)}, "
        f"{new.report_state or 'no validation record'})",
        "",
        "## Summary",
        "",
    ]
    for status in STATUS_ORDER:
        lines.append(f"- {STATUS_LABEL[status]}: {comparison.count(status)}")
    lines += ["", "## Competitor changes", ""]
    if not comparison.rows:
        lines += ["No competitors were found in either run.", ""]
    for row in comparison.rows:
        lines += [f"### {row.name} — {row.label}", ""]
        if row.status == NOT_OBSERVED:
            lines.append(
                "Not found in the latest research. This is a research observation, not evidence "
                "that the business has changed or closed."
            )
        for change in row.changes:
            tag = "observed" if change.certainty == "observed" else "inconclusive"
            lines.append(f"- **{change.label}** ({tag})")
            if change.before or change.after:
                lines.append(f"  - Baseline: {change.before}")
                lines.append(f"  - Latest: {change.after}")
            lines += [f"  - Source: {u}" for u in change.sources]
        if row.status in (NEW, UNCHANGED, NOT_OBSERVED):
            sources = row.latest_sources if row.status != NOT_OBSERVED else row.baseline_sources
            lines += [f"- Evidence: {u}" for u in sources]
        lines.append("")
    inconclusive = [
        (r.name, c) for r in comparison.rows for c in r.changes if c.certainty != "observed"
    ]
    lines += ["## Unverified or inconclusive observations", ""]
    lines += [f"- {n}: {c.label}" for n, c in inconclusive] or ["None."]
    lines += ["", "## Comparison limitations", ""]
    lines += [f"- {text}" for text in comparison.limitations]
    return "\n".join(lines) + "\n"
