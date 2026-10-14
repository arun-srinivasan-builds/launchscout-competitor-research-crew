"""Deterministic report validation, acceptance gate and partial-report tagging (PRP 7, 7.1)."""

from datetime import date

from launchscout.evidence import EvidenceEntry, EvidenceLedger
from launchscout.grounding import parse_competitors
from launchscout.links import LinkStatus
from launchscout.report import (
    build_final_report,
    report_filenames,
    section_keys,
    tag_unsupported_urls,
    tag_unverified_prices,
)
from launchscout.validation import (
    amounts_in,
    evaluate_gate,
    section_key,
    split_top_sections,
    table_rows,
    validate_report,
)
from tests.helpers import COMPETITORS_JSON, MENU_URLS, PARTIAL_REPORT_MD, PASS_REPORT_MD

TODAY = date(2026, 10, 14)


def ledger(*urls: str) -> EvidenceLedger:
    out = EvidenceLedger()
    for url in urls:
        out.add(EvidenceEntry(url=url, kind="search_result", accessed_on=TODAY))
    return out


def competitors():
    return parse_competitors(COMPETITORS_JSON).value


def good_ledger() -> EvidenceLedger:
    return ledger(*MENU_URLS, "https://millet-kitchen.example/")


def test_passing_report_is_validated_pass():
    result = validate_report(PASS_REPORT_MD, competitors(), good_ledger())
    assert result.state == "validated_pass"
    assert result.acceptance.result == "pass" and not result.acceptance.reasons
    assert result.section_keys == [
        "key_competitors",
        "complaints",
        "market_gap",
        "positioning",
        "launch_plan",
        "sources",
    ]
    assert result.eligible_competitors == 3 and result.verified_prices == 3
    assert result.competitor_rows == 3


def test_missing_report_is_failed_no_report():
    result = validate_report(None, competitors(), good_ledger())
    assert result.state == "failed_no_report"
    assert result.acceptance.result == "fail"
    assert validate_report("   ", None, good_ledger()).state == "failed_no_report"


def test_missing_section_and_order_violations_fail():
    gap_section = "## 3. Market Gap\nFew office-focused millet subscriptions.\n"
    no_gap = PASS_REPORT_MD.replace(gap_section, "")
    result = validate_report(no_gap, competitors(), good_ledger())
    assert result.state == "partial_failed_acceptance"
    assert any("missing section: Market Gap" in r for r in result.acceptance.reasons)

    swapped = (
        PASS_REPORT_MD.replace("## 3. Market Gap", "## 3. XTMP")
        .replace("## 4. Recommended Positioning", "## 3. Market Gap")
        .replace("## 3. XTMP", "## 4. Recommended Positioning")
    )
    result = validate_report(swapped, competitors(), good_ledger())
    assert any("order" in r for r in result.acceptance.reasons)


def test_extra_top_level_section_fails_exactly_six_rule():
    extra = PASS_REPORT_MD + "\n## 7. Bonus\nsomething\n"
    result = validate_report(extra, competitors(), good_ledger())
    assert any("unexpected top-level section" in r for r in result.acceptance.reasons)


def test_url_not_in_ledger_fails_and_is_listed():
    result = validate_report(PARTIAL_REPORT_MD, competitors(), good_ledger())
    assert result.state == "partial_failed_acceptance"
    r3 = next(r for r in result.rules if r.id == "R3")
    assert r3.status == "fail" and "https://made-up.example/source" in r3.items


def test_price_not_matching_verified_amount_fails():
    result = validate_report(PARTIAL_REPORT_MD, competitors(), good_ledger())
    r4 = next(r for r in result.rules if r.id == "R4")
    assert r4.status == "fail" and any("Green Tiffin" in i for i in r4.items)


def test_price_for_unverified_competitor_fails():
    raw = COMPETITORS_JSON.replace('"status": "verified"', '"status": "unknown"', 1)
    comps = parse_competitors(raw).value
    result = validate_report(PASS_REPORT_MD, comps, good_ledger())
    r4 = next(r for r in result.rules if r.id == "R4")
    assert r4.status == "fail" and "not verified" in r4.detail


def test_missing_weeks_and_recommendation_label_fail():
    text = PASS_REPORT_MD.replace("Week 3: pilot. ", "")
    text = text.replace("**Recommendation:**", "Suggested:")
    result = validate_report(text, competitors(), good_ledger())
    assert next(r for r in result.rules if r.id == "R5").status == "fail"
    assert next(r for r in result.rules if r.id == "R6").status == "fail"


def test_sources_must_cover_competitor_and_price_evidence():
    text = PASS_REPORT_MD.replace(f"- {MENU_URLS[2]}\n", "")
    result = validate_report(text, competitors(), good_ledger())
    r7 = next(r for r in result.rules if r.id == "R7")
    assert r7.status == "fail" and any("Hearty Bowls" in i for i in r7.items)


def test_gate_requires_three_verified_prices_even_if_report_is_well_formed():
    one = parse_competitors(
        COMPETITORS_JSON.replace('"status": "verified"', '"status": "unknown"')
    ).value
    reasons, eligible, verified = evaluate_gate(one, good_ledger())
    assert eligible == 3 and verified == 0
    assert any("verified price" in r for r in reasons)
    result = validate_report(PASS_REPORT_MD, one, good_ledger())
    assert result.state == "partial_failed_acceptance"


def test_gate_counts_only_prices_with_ledger_evidence():
    comps = competitors()
    thin = ledger(MENU_URLS[0], MENU_URLS[1], "https://millet-kitchen.example/")  # no Hearty URL
    reasons, _, verified = evaluate_gate(comps, thin)
    assert verified == 2 and reasons


def test_gate_missing_competitor_output():
    reasons, eligible, verified = evaluate_gate(None, good_ledger())
    assert eligible == verified == 0 and "missing" in reasons[0]


def test_broken_link_fails_but_blocked_and_unchecked_do_not():
    links = [
        LinkStatus(url=MENU_URLS[0], status="ok", code=200),
        LinkStatus(url=MENU_URLS[1], status="blocked", code=403, detail="HTTP 403"),
        LinkStatus(url=MENU_URLS[2], status="not_checked", detail="limit"),
    ]
    assert validate_report(PASS_REPORT_MD, competitors(), good_ledger(), links).state == (
        "validated_pass"
    )
    links.append(LinkStatus(url="https://x.example", status="broken", code=404, detail="HTTP 404"))
    result = validate_report(PASS_REPORT_MD, competitors(), good_ledger(), links)
    assert result.state == "partial_failed_acceptance"
    assert any("R8" in r for r in result.acceptance.reasons)


def test_parsing_helpers():
    assert section_key("1. Key Competitors") == "key_competitors"
    assert section_key("What Customers Complain About") == "complaints"
    assert section_key("**30-Day Launch Plan**") == "launch_plan"
    assert section_key("Random") is None
    rows = table_rows("| A | B |\n|---|---|\n| x | 1 |\n| y | 2 |\n\ntext")
    assert rows == [["x", "1"], ["y", "2"]]
    assert amounts_in("₹180 per box, Rs. 1,200 and 50 INR") == [180.0, 1200.0, 50.0]
    assert len(split_top_sections(PASS_REPORT_MD)) == 6
    assert section_keys(PASS_REPORT_MD)[0] == "key_competitors"


def test_partial_report_tags_in_place_and_never_drops_content():
    comps = competitors()
    unsupported = ["https://made-up.example/source"]
    tagged = tag_unsupported_urls(PARTIAL_REPORT_MD, unsupported)
    assert "https://made-up.example/source **[unverified link]**" in tagged
    assert tagged.count("made-up.example") == 1  # kept, not removed
    priced = tag_unverified_prices(PARTIAL_REPORT_MD, comps.competitors)
    assert "₹99 **[unverified price]** per box" in priced
    assert "₹180 **[unverified price]**" not in priced  # verified amount untouched


def test_markdown_link_to_unsupported_url_is_tagged_once():
    md = "See [source](https://made-up.example/x) and https://made-up.example/x too."
    out = tag_unsupported_urls(md, ["https://made-up.example/x"])
    assert "[source](https://made-up.example/x) **[unverified link]**" in out
    assert out.count("**[unverified link]**") == 2
    assert tag_unsupported_urls(out, ["https://made-up.example/x"]).count("[unverified link]") == 2


def test_final_report_headers_and_generated_verification_section():
    comps = competitors()
    led = good_ledger()
    ok = validate_report(PASS_REPORT_MD, comps, led)
    final_ok = build_final_report(PASS_REPORT_MD, ok, comps, None, None, led, "run-1")
    assert final_ok.startswith("> **Acceptance passed.**")
    assert "### Verification status" in final_ok
    assert "price status: verified" in final_ok and "evidence: https://" in final_ok

    bad = validate_report(PARTIAL_REPORT_MD, comps, led)
    final_bad = build_final_report(PARTIAL_REPORT_MD, bad, comps, None, None, led, "run-1")
    assert "FAILED ACCEPTANCE - PARTIAL RESEARCH" in final_bad.splitlines()[0]
    assert "[unverified link]" in final_bad and "[unverified price]" in final_bad


def test_report_filenames_depend_on_state():
    assert report_filenames("validated_pass") == ("report.md", "report.pdf")
    assert report_filenames("partial_failed_acceptance") == (
        "report-PARTIAL.md",
        "report-PARTIAL.pdf",
    )
    assert report_filenames("failed_no_report")[0] == "report-PARTIAL.md"


def test_acknowledged_unknown_amounts_do_not_fail_r4_or_get_tagged():
    import json

    data = json.loads(COMPETITORS_JSON)
    data["competitors"][1]["price"] = {"status": "unknown"}  # Green Tiffin unverified
    unverified = parse_competitors(json.dumps(data)).value
    row = (
        "| Green Tiffin | unknown; search-result amounts Rs 199 were not attributable "
        "| web | a | b | link |"
    )
    original = "| Green Tiffin | ₹150 per box | website | cheap | small | " + MENU_URLS[1] + " |"
    md = PASS_REPORT_MD.replace(original, row)
    res = validate_report(md, unverified, good_ledger())
    assert next(r for r in res.rules if r.id == "R4").status == "pass"
    assert "[unverified price]" not in tag_unverified_prices(md, unverified.competitors)
    # an unlabelled amount for an unverified competitor still fails and is tagged
    gone = "unknown; search-result amounts Rs 199 were not attributable"
    bare = md.replace(gone, "Rs 199 per box")
    again = validate_report(bare, unverified, good_ledger())
    assert next(r for r in again.rules if r.id == "R4").status == "fail"
    assert "[unverified price]" in tag_unverified_prices(bare, unverified.competitors)
