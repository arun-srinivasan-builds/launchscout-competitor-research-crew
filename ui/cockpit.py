"""Research Intelligence Cockpit: results view rendered only from a saved/in-memory snapshot.

Deterministic and read-only. It makes no model, search or research calls and writes nothing; every
number, label and sentence comes from stored evidence, validation results and structured outputs.
Model-written text (strategy, report) is always labelled as such.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st

from launchscout.comparison import build_comparison, pick_pair
from launchscout.evidence import EvidenceEntry, normalize_url
from launchscout.runner import RunSnapshot, get_manager
from launchscout.schemas import Competitor, ResearchMode
from launchscout.validation import section_key, split_top_sections
from ui.theme import inject_cockpit_theme
from ui.trace import fmt_elapsed, render_environment, render_trace_run

AREAS: tuple[str, ...] = (
    "Competitor Landscape",
    "Customer Voice",
    "Market Opportunity",
    "30-Day Launch Roadmap",
    "Evidence & Quality",
    "Engineering Trace",
)
AREA_KEY = "cockpit_area"
_TARGET = 3  # acceptance gate: competitors with evidence, and verified prices


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def _field(label: str, value_html: str) -> str:
    """A labelled value block. `value_html` must already be escaped."""
    return f'<div class="ck-field"><span class="ck-k">{_e(label)}</span>{value_html}</div>'


_MD_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://[^)\s]+)\)")
_PAREN_URL = re.compile(r"\s*\((?:see\s+)?https?://[^)\s]+\)")
_BARE_URL = re.compile(r"https?://\S+")


def _clean(text: str, limit: int = 220) -> str:
    """Readable prose for a card: links reduced to their label, URLs removed, clipped at a word."""
    text = _MD_LINK.sub(r"\1", text or "")
    text = _PAREN_URL.sub("", text)
    text = _BARE_URL.sub("", text)
    text = re.sub(r"[*_`]{1,3}", "", text)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:-")
    return cut + "\u2026"


def _first_sentence(text: str) -> str:
    """First sentence of `text` (split at '. ' or ': '), for one-line summaries."""
    cleaned = _clean(text, 400)
    match = re.search(r"(?<=[a-z0-9\)])[.](?=\s+[A-Z])", cleaned)
    return cleaned[: match.start() + 1] if match else cleaned


def _lower_first(text: str) -> str:
    """'A clearly ...' -> 'a clearly ...' (articles only, so names and acronyms are untouched)."""
    words = text.split()
    if words and words[0] in ("A", "An", "The"):
        return text[0].lower() + text[1:]
    return text


def _pct_class(value: int, target: int) -> str:
    pct = 0 if target <= 0 else min(100, int(round(100 * value / target / 5.0)) * 5)
    return f"ck-w-{pct}"


def _level(value: int, target: int) -> str:
    if value >= target:
        return ""
    return "ck-low" if value == 0 else "ck-mid"


# ---- source labels -------------------------------------------------------------------------


def _ledger_index(snap: RunSnapshot) -> dict[str, EvidenceEntry]:
    return {normalize_url(e.url): e for e in snap.evidence}


def source_label(url: str, ledger: dict[str, EvidenceEntry]) -> tuple[str, str]:
    """(readable label, provenance) for a URL. Provenance is derived from the ledger."""
    entry = ledger.get(normalize_url(url))
    parts = urlsplit(url)
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.strip("/")
    short_path = ("/" + path[:28] + ("…" if len(path) > 28 else "")) if path else ""
    fallback = f"{host}{short_path}"
    title = entry.title.strip() if entry and entry.title else ""
    label = f"{title[:70]}" if title else fallback
    if entry is None:
        origin = "not in evidence ledger"
    elif entry.kind == "scraped":
        origin = "page read" if entry.status == "ok" else "page read failed"
    else:
        origin = "search result"
    return label, origin


def source_link(url: str, ledger: dict[str, EvidenceEntry]) -> str:
    if not url.lower().startswith(("http://", "https://")):
        return _e(url)
    label, origin = source_label(url, ledger)
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    return (
        f'<span class="ck-src"><a href="{_e(url)}" target="_blank" rel="noopener noreferrer">'
        f"{_e(label)}</a><small>{_e(host)} · {_e(origin)}</small></span>"
    )


# ---- parsing of the stored report text (deterministic) --------------------------------------


def competitor_rows(markdown: str | None) -> dict[str, dict[str, str]]:
    """Key Competitors table of the report: {competitor name (lower): {header: cell}}."""
    if not markdown:
        return {}
    body = ""
    for heading, text in split_top_sections(markdown):
        if section_key(heading) == "key_competitors":
            body = text
            break
    rows: list[list[str]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) or not c for c in cells):
                continue
            rows.append(cells)
    if len(rows) < 2:
        return {}
    header = [h.lower() for h in rows[0]]
    out: dict[str, dict[str, str]] = {}
    for cells in rows[1:]:
        row = {header[i]: cells[i] for i in range(min(len(header), len(cells)))}
        name = re.sub(r"[*_`]", "", cells[0]).strip().lower()
        out[name] = row
    return out


def _cell(row: dict[str, str], *keywords: str) -> str:
    for key, value in row.items():
        if any(k in key for k in keywords):
            return re.sub(r"\*\*|\[unverified [a-z]+\]|\[|\]\([^)]*\)", "", value).strip()
    return ""


_WEEK_SPLIT = re.compile(r"(?=\bWeek\s*[1-4]\b)", re.IGNORECASE)
_WEEK_HEAD = re.compile(r"^[\s#*_\-]*week\s*([1-4])\b[\s:.–—\-)*_]*(.*)$", re.IGNORECASE)


def parse_roadmap(markdown: str | None) -> list[tuple[int, str, list[str]]]:
    """(week, title, actions) for Weeks 1-4 from the launch-plan section; [] if unparseable."""
    if not markdown:
        return []
    body = ""
    for heading, text in split_top_sections(markdown):
        if section_key(heading) == "launch_plan":
            body = text
            break
    weeks: dict[int, tuple[str, list[str]]] = {}
    current: int | None = None
    for raw in body.splitlines():
        for segment in _WEEK_SPLIT.split(raw):
            line = segment.strip()
            if not line:
                continue
            head = _WEEK_HEAD.match(line)
            if head:
                current = int(head.group(1))
                rest = re.sub(r"[*_`]", "", head.group(2)).strip()
                title = rest.strip(" .:-")
                weeks.setdefault(current, ("", []))
                # a sentence ("Week 1: research.") is an action; a short label is a title
                if title and len(title) < 60 and not rest.endswith("."):
                    weeks[current] = (title, weeks[current][1])
                elif title:
                    weeks[current][1].append(title)
            elif current is not None:
                action = re.sub(r"^[-*•]\s+|^\d+[.)]\s+", "", line)
                action = re.sub(r"\*\*|`", "", action).strip()
                if action:
                    weeks[current][1].append(action)
    return [(w, weeks[w][0], weeks[w][1]) for w in sorted(weeks)]


def _assumptions(markdown: str | None) -> list[str]:
    if not markdown:
        return []
    for heading, text in split_top_sections(markdown):
        if section_key(heading) == "positioning":
            lines = text.splitlines()
            out: list[str] = []
            capture = False
            for line in lines:
                if re.search(r"assumption", line, re.I):
                    capture = True
                    continue
                if capture and re.match(r"^\s*[-*]\s+", line):
                    out.append(re.sub(r"^\s*[-*]\s+|\*\*", "", line).strip())
                elif capture and line.strip() and not line.strip().startswith(("-", "*")):
                    break
            return out
    return []


# ---- executive summary -----------------------------------------------------------------------


def _crew_chip(snap: RunSnapshot) -> str:
    done = len(snap.completed_tasks)
    mode = "hierarchical" if snap.mode is ResearchMode.HIERARCHICAL else "sequential"
    took = fmt_elapsed(snap.elapsed_seconds())
    if snap.status == "complete":
        return (
            f'<span class="ck-chip ck-ok"><span class="ck-dot"></span>Crew completed '
            f"<small>{done}/4 agents · {took} · {mode}</small></span>"
        )
    names = {
        "partial": "Crew partial",
        "failed": "Crew failed",
        "cancelled": "Crew cancelled",
        "timeout": "Crew timed out",
        "running": "Crew running",
        "created": "Crew not started",
    }
    kind = "ck-warn" if snap.status in ("partial", "cancelled", "timeout") else "ck-bad"
    return (
        f'<span class="ck-chip {kind}"><span class="ck-dot"></span>'
        f"{names.get(snap.status, snap.status)} "
        f"<small>{done}/4 agents · {took} · {mode}</small></span>"
    )


def _acceptance_chip(snap: RunSnapshot) -> str:
    state = snap.report_state
    if state == "validated_pass":
        return (
            '<span class="ck-chip ck-ok"><span class="ck-dot"></span>Report validated '
            "<small>all checks passed</small></span>"
        )
    if state == "partial_failed_acceptance":
        return (
            '<span class="ck-chip ck-bad"><span class="ck-dot"></span>Report failed acceptance '
            "<small>partial research</small></span>"
        )
    if state == "failed_no_report":
        return '<span class="ck-chip ck-bad"><span class="ck-dot"></span>No report produced</span>'
    if snap.report_markdown:
        return (
            '<span class="ck-chip"><span class="ck-dot"></span>Acceptance not evaluated '
            "<small>saved before validation existed</small></span>"
        )
    return '<span class="ck-chip"><span class="ck-dot"></span>No report</span>'


def _kpi(value: int, target: int | None, label: str) -> str:
    of = f'<span class="ck-kpi-of">/ {target}</span>' if target is not None else ""
    bar = ""
    if target:
        level = _level(value, target)
        bar = (
            f'<div class="ck-bar"><div class="ck-fill {level} {_pct_class(value, target)}">'
            "</div></div>"
        )
    return (
        f'<div class="ck-kpi"><div class="ck-kpi-top"><span class="ck-kpi-val">{value}</span>'
        f'{of}</div><div class="ck-kpi-label">{_e(label)}</div>{bar}</div>'
    )


def takeaway(snap: RunSnapshot) -> str:
    """One paragraph built only from stored counts and fields (no model involved)."""
    comps = snap.competitors.competitors if snap.competitors else []
    city = _e(snap.input.city)
    parts: list[str] = []
    if comps:
        names = ", ".join(_e(c.name) for c in comps[:3])
        parts.append(
            f"The crew found <b>{len(comps)} competitor{'s' if len(comps) != 1 else ''}</b> in "
            f"{city} with retrieved evidence ({names}{'…' if len(comps) > 3 else ''})."
        )
    else:
        parts.append("No competitor could be supported with retrieved evidence.")
    verified = [c for c in comps if c.price.status == "verified"]
    if comps and not verified:
        parts.append("No per-unit price could be verified from the pages that were read.")
    elif verified:
        parts.append(f"<b>{len(verified)}</b> competitor price(s) were verified in page text.")
    findings = snap.reviews.findings if snap.reviews else []
    if findings:
        sourced = sum(1 for f in findings if f.source_url)
        parts.append(
            f"{len(findings)} customer finding(s) were retrieved, {sourced} with a source."
        )
    strategy = snap.strategy
    if strategy and (strategy.recommended_offer or strategy.recommended_price):
        offer = _e(_lower_first(_clean(_first_sentence(strategy.recommended_offer), 130)))
        price = _e(_clean(_first_sentence(strategy.recommended_price), 80))

        def sentence(value: str) -> str:
            return value if value.endswith(("…", ".", "!", "?")) else value + "."

        text = "The strategy proposes " + sentence(offer or "an offer")
        if price:
            text += " Suggested price: " + sentence(price)
        parts.append(text + " <i>(a recommendation, not a verified fact)</i>")
    return " ".join(parts)


def _summary(snap: RunSnapshot) -> None:
    v = snap.validation
    comps = snap.competitors.competitors if snap.competitors else []
    eligible = v.eligible_competitors if v else sum(1 for c in comps if c.evidence_urls)
    verified = v.verified_prices if v else sum(1 for c in comps if c.price.status == "verified")
    rules = v.rules if v else []
    passed = sum(1 for r in rules if r.status == "pass")
    pages = sum(1 for e in snap.evidence if e.kind == "scraped" and e.status == "ok")
    kpis = [
        _kpi(eligible, _TARGET, "Competitors with evidence"),
        _kpi(verified, _TARGET, "Competitors with a verified price"),
    ]
    if rules:
        kpis.append(_kpi(passed, len(rules), "Quality checks passed"))
    kpis.append(_kpi(len(snap.completed_tasks), 4, "Agents completed"))
    kpis.append(_kpi(len(snap.evidence), None, "URLs discovered"))
    kpis.append(_kpi(pages, None, "Pages read"))

    block = ""
    if v and v.state == "partial_failed_acceptance":
        reasons = "".join(f"<li>{_e(r)}</li>" for r in _unique_reasons(v.acceptance.reasons)[:4])
        block = (
            '<div class="ck-block"><b>Why acceptance did not pass</b> '
            f"(research finished, evidence was insufficient)<ul>{reasons}</ul></div>"
        )
    elif v and v.state == "validated_pass":
        block = (
            '<div class="ck-block ck-pass"><b>Validated.</b> Every deterministic check '
            "passed; recommendations remain labelled as proposals.</div>"
        )
    elif v and v.state == "failed_no_report" and snap.status == "complete":
        block = '<div class="ck-block"><b>No report was produced</b>; nothing to validate.</div>'
    elif snap.status in ("failed", "cancelled", "timeout", "partial") and not snap.report_markdown:
        reason = {
            "failed": "The run failed before a report could be produced.",
            "cancelled": "The run was cancelled; only completed task outputs exist.",
            "timeout": "The run hit its time limit and was stopped.",
            "partial": "Some tasks did not finish; no report was produced.",
        }[snap.status]
        detail = f" <i>{_e(snap.error)}</i>" if snap.error else ""
        block = f'<div class="ck-block"><b>{_e(reason)}</b>{detail}</div>'
    elif snap.report_markdown:
        block = (
            '<div class="ck-block">This run was saved before report validation existed. The '
            "report is the Writer's draft exactly as saved; nothing was regenerated.</div>"
        )

    st.markdown(
        '<div class="ck-wrap ck-hero"><div class="ck-eyebrow">Research intelligence · '
        f"{_e(snap.input.idea)} · {_e(snap.input.city)}</div>"
        f'<div class="ck-chips">{_crew_chip(snap)}{_acceptance_chip(snap)}</div>'
        f'<div class="ck-take">{takeaway(snap)}</div>'
        f'<div class="ck-kpis">{"".join(kpis)}</div>{block}</div>',
        unsafe_allow_html=True,
    )


def _unique_reasons(reasons: list[str]) -> list[str]:
    """Drop gate reasons that restate a rule failure (avoid saying one thing twice)."""
    seen: list[str] = []
    for reason in reasons:
        key = re.sub(r"^R\d+\s+[^:]+:\s*", "", reason).lower()
        if "competitor row" in key and any("name, url and evidence" in s.lower() for s in seen):
            continue
        if reason not in seen:
            seen.append(reason)
    return seen


# ---- areas -----------------------------------------------------------------------------------


def _price_badge(comp: Competitor) -> str:
    p = comp.price
    if p.status == "verified" and p.amount is not None:
        return f'<span class="ck-badge ck-ok">{p.amount:g} {_e(p.currency)} / {_e(p.unit)}</span>'
    return '<span class="ck-badge ck-warn">Price unknown</span>'


def _area_competitors(snap: RunSnapshot) -> None:
    comps = snap.competitors.competitors if snap.competitors else []
    if not comps:
        st.info("No competitor profile was produced for this run.")
        return
    ledger = _ledger_index(snap)
    table = competitor_rows(snap.report_markdown)
    cards: list[str] = []
    for comp in comps:
        row = table.get(re.sub(r"[*_`]", "", comp.name).strip().lower(), {})
        strength = _cell(row, "strength")
        weakness = _cell(row, "weak")
        host = urlsplit(comp.url).netloc.lower().removeprefix("www.")
        tags = "".join(
            f'<span class="ck-tag">{_e(_clean(c, 38))}</span>'
            for c in comp.channels[:4]
            if _clean(c, 38)
        )
        sources = (
            "".join(f"<div>{source_link(u, ledger)}</div>" for u in comp.evidence_urls[:4])
            or '<div class="ck-site">No evidence URL was returned by a tool.</div>'
        )
        fields = [_field("Offer", _e(_clean(comp.offer, 200) or "unknown"))]
        if strength:
            fields.append(_field("Strength", _e(_clean(strength, 240))))
        if weakness:
            fields.append(_field("Gap or weakness", _e(_clean(weakness, 240))))
        if tags:
            fields.append(f'<div class="ck-tags">{tags}</div>')
        fields.append(_field("Evidence", f'<div class="ck-srcs">{sources}</div>'))
        cards.append(
            '<div class="ck-card"><div class="ck-card-head"><div>'
            f'<h4>{_e(comp.name)}</h4><div class="ck-site">{_e(host)}</div></div>'
            f"{_price_badge(comp)}</div>{''.join(fields)}</div>"
        )
    st.markdown(f'<div class="ck-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    for comp in comps:
        if comp.unknowns:
            with st.expander(f"Not evidenced for {comp.name} ({len(comp.unknowns)})"):
                for item in comp.unknowns:
                    st.markdown(f"- {item}")
    if snap.competitors and snap.competitors.shortfall_reason:
        st.caption(f"Shortfall stated by the agent: {snap.competitors.shortfall_reason}")


def _area_voice(snap: RunSnapshot) -> None:
    findings = snap.reviews.findings if snap.reviews else []
    ledger = _ledger_index(snap)
    if not findings:
        st.info("No attributable customer findings were retrieved for this run.")
    else:
        sourced = sum(1 for f in findings if f.source_url)
        praise = sum(1 for f in findings if f.kind == "praise")
        st.markdown(
            f'<div class="ck-chips"><span class="ck-chip ck-ok">{praise} praise</span>'
            f'<span class="ck-chip ck-bad">{len(findings) - praise} complaint</span>'
            f'<span class="ck-chip">{sourced} with a source</span></div>',
            unsafe_allow_html=True,
        )
        by_comp: dict[str, list] = {}
        for f in findings:
            by_comp.setdefault(f.competitor, []).append(f)
        for name, items in by_comp.items():
            with st.expander(f"{name} ({len(items)})", expanded=len(by_comp) <= 2):
                for f in items:
                    cls = "ck-quote ck-complaint" if f.kind == "complaint" else "ck-quote"
                    src = (
                        source_link(f.source_url, ledger)
                        if f.source_url
                        else ('<span class="ck-badge ck-warn">inferred, no source</span>')
                    )
                    st.markdown(
                        f'<div class="{cls}">{_e(f.text)}<div class="ck-note">'
                        f'<span class="ck-badge">{_e(f.basis)}</span> {_e(f.kind)} · {src}'
                        "</div></div>",
                        unsafe_allow_html=True,
                    )
    gaps = snap.reviews.gaps if snap.reviews else []
    if gaps:
        with st.expander(f"What could not be retrieved ({len(gaps)})"):
            for g in gaps:
                st.markdown(f"- {g}")


def _area_opportunity(snap: RunSnapshot) -> None:
    s = snap.strategy
    if s is None or not (s.market_gap or s.recommended_offer):
        st.info("No strategy output was produced for this run.")
        return
    ledger = _ledger_index(snap)
    refs = "".join(f"<div>{source_link(u, ledger)}</div>" for u in s.evidence_refs[:5])
    gap_fields = [_field("Gap", _e(s.market_gap or "unknown"))]
    if refs:
        gap_fields.append(_field("Supporting sources", f'<div class="ck-srcs">{refs}</div>'))
    price = (
        _e(s.recommended_price or "unknown") + ' <span class="ck-badge ck-rec">not a fact</span>'
    )
    offer_fields = [
        _field("Offer", _e(s.recommended_offer or "unknown")),
        _field("Positioning", _e(s.positioning_line or "unknown")),
        _field("Price", price),
    ]
    gap_card = (
        '<div class="ck-card"><div class="ck-card-head"><h4>Market gap</h4>'
        '<span class="ck-badge ck-warn">interpretation</span></div>'
        + "".join(gap_fields)
        + "</div>"
    )
    offer_card = (
        '<div class="ck-card"><div class="ck-card-head"><h4>Proposed offer</h4>'
        '<span class="ck-badge ck-rec">Recommendation</span></div>'
        + "".join(offer_fields)
        + "</div>"
    )
    st.markdown(f'<div class="ck-grid">{gap_card}{offer_card}</div>', unsafe_allow_html=True)
    if s.rationale:
        with st.expander("Strategy rationale (model-written)"):
            st.markdown(s.rationale)
    assumptions = _assumptions(snap.report_markdown)
    if assumptions:
        with st.expander(f"Assumptions stated in the report ({len(assumptions)})"):
            for a in assumptions:
                st.markdown(f"- {a}")


def _area_roadmap(snap: RunSnapshot) -> None:
    weeks = parse_roadmap(snap.report_markdown)
    if not weeks:
        st.info("The launch plan could not be parsed from the saved report; open the full report.")
        return
    cards = []
    for week, title, actions in weeks:
        items = "".join(f"<li>{_e(_clean(a, 150))}</li>" for a in actions[:4])
        cards.append(
            f'<div class="ck-week"><div class="ck-week-num">WEEK {week}</div>'
            + (f"<h5>{_e(title)}</h5>" if title else "")
            + f"<ul>{items}</ul></div>"
        )
    st.markdown(f'<div class="ck-road">{"".join(cards)}</div>', unsafe_allow_html=True)
    st.caption("Launch actions are the Report Writer's proposals, not researched facts.")


def _area_quality(snap: RunSnapshot) -> None:
    v = snap.validation
    if v is None:
        st.info("This run has no validation results (saved before validation existed).")
    else:
        rows = []
        for r in v.rules:
            cls = {"pass": "ck-ok", "fail": "ck-bad"}.get(r.status, "")
            rows.append(
                f'<div class="ck-rule"><span class="ck-rule-id">{_e(r.id)}</span><div>'
                f'<div class="ck-rule-title">{_e(r.title)}</div>'
                f'<div class="ck-rule-detail">{_e(r.detail)}</div></div>'
                f'<span class="ck-badge {cls}">{_e(r.status.upper())}</span></div>'
            )
        st.markdown(
            f'<div class="ck-h">Quality checks ({sum(1 for r in v.rules if r.status == "pass")}'
            f"/{len(v.rules)} passed)</div>"
            f'<div class="ck-rules">{"".join(rows)}</div>'
            f'<div class="ck-note">Gate: {v.eligible_competitors} competitor(s) with evidence '
            f"and {v.verified_prices} with a verified price (3 required for each).</div>",
            unsafe_allow_html=True,
        )
        items = [i for r in v.failed_rules for i in r.items]
        if items:
            with st.expander(f"Unsupported or unverified items ({len(items)})"):
                for item in items[:30]:
                    st.markdown(f"- {item}")
        if v.links:
            st.markdown(
                '<div class="ck-h">Link reachability</div><div class="ck-note">HTTP reachability '
                "only: a reachable page does not prove it supports a claim. Price amounts are "
                "checked separately against the stored page text.</div>",
                unsafe_allow_html=True,
            )
            ledger = _ledger_index(snap)
            rows = []
            for lk in v.links:
                cls = {"ok": "ck-ok", "broken": "ck-bad", "blocked": "ck-warn"}.get(lk.status, "")
                basis = "read during research" if lk.source == "research" else lk.detail
                rows.append(
                    f'<div class="ck-rule"><span class="ck-badge {cls}">{_e(lk.status)}</span>'
                    f"<div>{source_link(lk.url, ledger)}</div>"
                    f'<span class="ck-rule-detail">{_e(basis)}</span></div>'
                )
            st.markdown(f'<div class="ck-rules">{"".join(rows)}</div>', unsafe_allow_html=True)
    if snap.grounding_issues:
        with st.expander(f"Guardrail findings ({len(snap.grounding_issues)})"):
            for issue in snap.grounding_issues:
                st.markdown(f"- {issue}")
    kinds = {}
    for e in snap.evidence:
        kinds[(e.kind, e.status)] = kinds.get((e.kind, e.status), 0) + 1
    if kinds:
        summary = ", ".join(
            f"{n} {k[0].replace('_', ' ')} ({k[1]})" for k, n in sorted(kinds.items())
        )
        st.caption(f"Evidence ledger: {summary}.")


def _comparison_panel(snap: RunSnapshot) -> None:
    """Sequential vs hierarchical from recorded runs with the same input (never projected)."""
    sequential, hierarchical = pick_pair(get_manager().runs_dir(), snap)
    rows = build_comparison(sequential, hierarchical)
    with st.expander("Mode comparison: sequential vs hierarchical (recorded runs only)"):
        st.caption(
            "Both columns come from saved runs with identical input. 'Not yet measured' means no "
            "such run exists; nothing is estimated. Task completion only says the agents "
            "finished; research quality is the evidence and the validation result."
        )
        st.dataframe(
            [
                {
                    "Group": r.group,
                    "Metric": r.metric,
                    "Sequential": r.sequential,
                    "Hierarchical": r.hierarchical,
                }
                for r in rows
            ],
            hide_index=True,
            width="stretch",
        )


def _area_trace(snap: RunSnapshot) -> None:
    u = snap.usage
    m = snap.agent_metrics()
    refused = int(sum(r["refused_budget"] for r in m.values()))
    errors = int(sum(r["tool_errors"] for r in m.values()))
    tiles = [
        _kpi(u.llm_calls or 0, None, "Model calls"),
        _kpi(u.total_tokens or 0, None, "Tokens (measured)"),
        _kpi(u.serper_calls or 0, None, "Searches"),
        _kpi(u.scrape_calls or 0, None, "Pages read"),
        _kpi(refused, None, "Budget refusals"),
        _kpi(errors, None, "Tool errors"),
    ]
    if snap.mode is ResearchMode.HIERARCHICAL:
        mgr = m.get("Research Manager", {})
        tiles += [
            _kpi(int(mgr.get("llm_calls", 0)), None, "Manager model calls"),
            _kpi(int(mgr.get("delegations", 0)), None, "Delegations"),
        ]
    st.markdown(f'<div class="ck-kpis">{"".join(tiles)}</div>', unsafe_allow_html=True)
    st.caption("Counts are measured from the saved run events; nothing is estimated.")
    _comparison_panel(snap)
    with st.expander(
        "Engineering Trace: events, tool calls, evidence ledger, usage per agent", expanded=False
    ):
        render_trace_run(snap)
        render_environment()


_RENDERERS = {
    "Competitor Landscape": _area_competitors,
    "Customer Voice": _area_voice,
    "Market Opportunity": _area_opportunity,
    "30-Day Launch Roadmap": _area_roadmap,
    "Evidence & Quality": _area_quality,
    "Engineering Trace": _area_trace,
}


def _navigation() -> str:
    """Six pills. Business intelligence (first four) and trust and engineering (last two) are
    separated by CSS on the keyed container, with no extra headings."""
    default = AREAS[0]
    if st.session_state.get(AREA_KEY) not in AREAS:
        st.session_state[AREA_KEY] = default
    with st.container(key="ck_nav"):
        if hasattr(st, "pills"):
            choice = st.pills(
                "Explore",
                AREAS,
                selection_mode="single",
                key=AREA_KEY,
                label_visibility="collapsed",
            )
        else:  # older Streamlit: same behaviour with a horizontal radio
            choice = st.radio(
                "Explore", AREAS, horizontal=True, key=AREA_KEY, label_visibility="collapsed"
            )
    return choice if choice in AREAS else default


def _downloads_row(snap: RunSnapshot) -> None:
    """Actions row directly under the summary: both downloads, equal size. Reads stored files."""
    if not snap.run_dir or not snap.report_files:
        return
    root = Path(snap.run_dir)
    if snap.report_state is None:
        suffix, tag = " (UNVALIDATED)", "saved draft, never validated"
    elif snap.report_state != "validated_pass":
        suffix, tag = " (PARTIAL)", "partial, not validated"
    else:
        suffix, tag = "", "validated"
    specs = (
        ("md", "Download Markdown", "text/markdown"),
        ("pdf", "Download PDF", "application/pdf"),
    )
    with st.container(key="ck_actions"):
        st.markdown(
            f'<div class="ck-actions-title">Report downloads · {_e(tag)}</div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(2)
        for column, (kind, label, mime) in zip(columns, specs, strict=True):
            name = snap.report_files.get(kind)
            path = root / name if name else None
            if path is None or not path.is_file():
                column.caption(f"{label.split()[-1]} not available for this run.")
                continue
            column.download_button(
                label + suffix,
                data=path.read_bytes(),
                file_name=name,
                mime=mime,
                key=f"ck_dl_{kind}_{snap.run_id}",
                width="stretch",
            )


def render(snap: RunSnapshot) -> None:
    """Render the cockpit for one finished run (replaces the long results page)."""
    inject_cockpit_theme()
    _summary(snap)
    _downloads_row(snap)
    area = _navigation()
    _RENDERERS[area](snap)
    if snap.report_markdown:
        label = {
            "validated_pass": "Full original six-section report (validated)",
            "partial_failed_acceptance": (
                "Full original six-section report (PARTIAL, not validated)"
            ),
        }.get(snap.report_state or "", "Full report as saved (never validated)")
        with st.expander(label, expanded=False):
            st.markdown(snap.report_markdown)
